# Tachyon - Fast Multi-Threaded Web Discovery Tool
# Copyright (c) 2011 Gabriel Tremblay - initnull hat gmail.com
#
# GNU General Public Licence (GPL)
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 59 Temple
# Place, Suite 330, Boston, MA  02111-1307  USA

from unittest import TestCase
from unittest.mock import MagicMock, call, patch
from hammertime.core import HammerTime
from hammertime.ruleset import RejectRequest, StopRequest

from tachyon.core import database
from tachyon.core.database import valid_paths
from tachyon.core.directoryfetcher import DirectoryFetcher
from fixtures import async, FakeHammerTimeEngine, RaiseForPaths, SetResponseCode, create_json_data


@patch("tachyon.core.textutils.output_found")
class TestDirectoryFetcher(TestCase):

    def setUp(self):
        valid_paths.clear()
        database.successful_fetch_count = 0
        self.host = "http://example.com"

    def async_setup(self, loop):
        self.hammertime = HammerTime(loop=loop, request_engine=FakeHammerTimeEngine())
        self.directory_fetcher = DirectoryFetcher(self.host, self.hammertime)

    @async()
    async def test_fetch_paths_add_valid_path_to_database(self, output_found, loop):
        valid = ["/a", "b", "/c", "/1", "/2", "/3"]
        invalid = ["/d", "/e", "/4", "/5"]
        paths = valid + invalid
        self.async_setup(loop)
        self.hammertime.heuristics.add(RaiseForPaths(invalid, RejectRequest("Invalid path")))

        await self.directory_fetcher.fetch_paths(create_json_data(paths))

        self.assertEqual(len(valid), len(valid_paths))
        for path in valid_paths:
            self.assertIn(path["url"], valid)
            self.assertNotIn(path["url"], invalid)

    @async()
    async def test_fetch_paths_update_successful_fetch_count(self, output_found, loop):
        successful = ["/a", "/b", "/c"]
        timeout = ["/1", "/2", "/3"]
        paths = timeout + successful
        self.async_setup(loop)
        self.hammertime.heuristics.add(RaiseForPaths(timeout, StopRequest()))

        await self.directory_fetcher.fetch_paths(create_json_data(paths))

        self.assertEqual(len(successful), database.successful_fetch_count)

    @async()
    async def test_fetch_paths_dont_add_path_if_response_code_is_401(self, output_found, loop):
        paths = ["/401"]
        self.async_setup(loop)
        self.hammertime.heuristics.add(SetResponseCode(401))

        await self.directory_fetcher.fetch_paths(create_json_data(paths))

        self.assertEqual(len(database.valid_paths), 0)

    @async()
    async def test_fetch_paths_output_found_directory(self, output_found, loop):
        found = ["/%d" % i for i in range(10)]
        not_found = ["/1%d" % i for i in range(10)]
        paths = found + not_found
        self.async_setup(loop)
        self.hammertime.heuristics.add(RaiseForPaths(not_found, RejectRequest("404 not found")))

        await self.directory_fetcher.fetch_paths(create_json_data(paths))

        calls = []
        for path in create_json_data(found):
            data = {
                "description": path["description"],
                "url": self.host + path["url"],
                "code": 200,
                "severity": path['severity']
            }
            _call = call(path["description"] + ' at: ' + self.host + path["url"], data)
            calls.append(_call)
        output_found.assert_has_calls(calls, any_order=True)

    @async()
    async def test_fetch_paths_output_401_directory(self, output_found, loop):
        self.async_setup(loop)
        self.hammertime.heuristics.add(SetResponseCode(401))

        await self.directory_fetcher.fetch_paths(create_json_data(["/admin"]))
        desc = "description of admin"
        data = {
            "description": desc,
            "url": self.host + "/admin",
            "code": 401,
            "severity": "warning"
        }
        message = "Password Protected - " + desc + " at: " + self.host + "/admin"
        output_found.assert_called_once_with(message, data)

    @async()
    async def test_fetch_paths_output_500_response(self, output_found, loop):
        self.async_setup(loop)
        self.hammertime.heuristics.add(SetResponseCode(500))

        await self.directory_fetcher.fetch_paths(create_json_data(["/server-error"]))
        desc = "description of server-error"
        data = {
            "description": desc,
            "url": self.host + "/server-error",
            "code": 500,
            "severity": "warning"
        }
        message = "ISE, " + desc + " at: " + self.host + "/server-error"
        output_found.assert_called_once_with(message, data)

    @async()
    async def test_fetch_paths_output_403_directory(self, output_found, loop):
        self.async_setup(loop)
        self.hammertime.heuristics.add(SetResponseCode(403))

        await self.directory_fetcher.fetch_paths(create_json_data(["/forbidden"]))
        desc = "description of forbidden"
        data = {
            "description": desc,
            "url": self.host + "/forbidden",
            "code": 403,
            "severity": "warning"
        }
        message = "*Forbidden* " + desc + " at: " + self.host + "/forbidden"
        output_found.assert_called_once_with(message, data)

    @async()
    async def test_fetch_paths_output_tomcat_fake_404(self, output_found, loop):
        self.async_setup(loop)
        self.hammertime.heuristics.add(SetResponseCode(404))

        with patch("tachyon.core.workers.detect_tomcat_fake_404", MagicMock(return_value=True)):
            await self.directory_fetcher.fetch_paths(create_json_data(["/path"]))
            desc = "description of path"
            data = {
                "description": desc,
                "url": self.host + "/path",
                "code": 404,
                "severity": "warning",
                "special": "tomcat-redirect"
            }
            message = "Tomcat redirect, " + desc + " at: " + self.host + "/path"
            output_found.assert_called_once_with(message, data)
