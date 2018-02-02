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
from hammertime.http import StaticResponse
from urllib.parse import urlparse

from tachyon.core import database
from tachyon.core.database import valid_paths
from tachyon.core.directoryfetcher import DirectoryFetcher
from fixtures import async
from tachyon.core import textutils


class TestDiscoveryFetcher(TestCase):

    def setUp(self):
        valid_paths.clear()
        database.successful_fetch_count = 0

    @async()
    async def test_fetch_paths_add_valid_path_to_database(self, loop):
        valid = ["/a", "b", "/c", "/1", "/2", "/3"]
        invalid = ["/d", "/e", "/4", "/5"]
        paths = valid + invalid
        hammertime = HammerTime(loop=loop, request_engine=FakeHammertimeEngine())
        hammertime.heuristics.add(RaiseForPaths(invalid, RejectRequest("Invalid path")))
        directory_fetcher = DirectoryFetcher("http://example.com", hammertime)

        await directory_fetcher.fetch_paths(self.to_json_data(paths))

        self.assertEqual(len(valid), len(valid_paths))
        for path in valid_paths:
            self.assertIn(path["url"], valid)
            self.assertNotIn(path["url"], invalid)

    @async()
    async def test_fetch_paths_update_successful_fetch_count(self, loop):
        successful = ["/a", "/b", "/c"]
        timeout = ["/1", "/2", "/3"]
        paths = timeout + successful
        hammertime = HammerTime(loop=loop, request_engine=FakeHammertimeEngine())
        hammertime.heuristics.add(RaiseForPaths(timeout, StopRequest()))
        directory_fetcher = DirectoryFetcher("http://example.com", hammertime)

        await directory_fetcher.fetch_paths(self.to_json_data(paths))

        self.assertEqual(len(successful), database.successful_fetch_count)

    @async()
    async def test_fetch_paths_dont_add_path_if_response_code_is_401(self, loop):
        paths = ["/401"]
        hammertime = HammerTime(loop=loop, request_engine=FakeHammertimeEngine())
        directory_fetcher = DirectoryFetcher("http://example.com", hammertime)
        hammertime.heuristics.add(SetResponseCode(401))

        await directory_fetcher.fetch_paths(self.to_json_data(paths))

        self.assertEqual(len(database.valid_paths), 0)

    @async()
    async def test_fetch_paths_output_found_directory(self, loop):
        found = ["/%d" % i for i in range(10)]
        not_found = ["/1%d" % i for i in range(10)]
        paths = found + not_found
        hammertime = HammerTime(loop=loop, request_engine=FakeHammertimeEngine())
        hammertime.heuristics.add(RaiseForPaths(not_found, RejectRequest("404 not found")))
        base_url = "http://example.com"
        directory_fetcher = DirectoryFetcher(base_url, hammertime)

        with patch("tachyon.core.textutils.output_found", MagicMock()):

            await directory_fetcher.fetch_paths(self.to_json_data(paths))

            calls = []
            for path in self.to_json_data(found):
                data = {
                    "description": path["description"],
                    "url": base_url + path["url"],
                    "code": 200,
                    "severity": path['severity']
                }
                _call = call(path["description"] + ' at: ' + base_url + path["url"], data)
                calls.append(_call)
            textutils.output_found.assert_has_calls(calls, any_order=True)

    @async()
    async def test_fetch_paths_output_401_directory(self, loop):
        hammertime = HammerTime(loop=loop, request_engine=FakeHammertimeEngine())
        hammertime.heuristics.add(SetResponseCode(401))
        base_url = "http://example.com"
        directory_fetcher = DirectoryFetcher(base_url, hammertime)

        with patch("tachyon.core.textutils.output_found", MagicMock()):
            await directory_fetcher.fetch_paths(self.to_json_data(["/admin"]))
            desc = "admin"
            data = {
                "description": desc,
                "url": base_url + "/admin",
                "code": 401,
                "severity": "warning"
            }
            message = "Password Protected - " + desc + " at: " + base_url + "/admin"
            textutils.output_found.assert_called_once_with(message, data)

    @async()
    async def test_fetch_paths_output_500_response(self, loop):
        hammertime = HammerTime(loop=loop, request_engine=FakeHammertimeEngine())
        hammertime.heuristics.add(SetResponseCode(500))
        base_url = "http://example.com"
        directory_fetcher = DirectoryFetcher(base_url, hammertime)

        with patch("tachyon.core.textutils.output_found", MagicMock()):
            await directory_fetcher.fetch_paths(self.to_json_data(["/server-error"]))
            desc = "server-error"
            data = {
                "description": desc,
                "url": base_url + "/server-error",
                "code": 500,
                "severity": "warning"
            }
            message = "ISE, " + desc + " at: " + base_url + "/server-error"
            textutils.output_found.assert_called_once_with(message, data)

    @async()
    async def test_fetch_paths_output_403_directory(self, loop):
        hammertime = HammerTime(loop=loop, request_engine=FakeHammertimeEngine())
        hammertime.heuristics.add(SetResponseCode(403))
        base_url = "http://example.com"
        directory_fetcher = DirectoryFetcher(base_url, hammertime)

        with patch("tachyon.core.textutils.output_found", MagicMock()):
            await directory_fetcher.fetch_paths(self.to_json_data(["/forbidden"]))
            desc = "forbidden"
            data = {
                "description": desc,
                "url": base_url + "/forbidden",
                "code": 403,
                "severity": "warning"
            }
            message = "*Forbidden* " + desc + " at: " + base_url + "/forbidden"
            textutils.output_found.assert_called_once_with(message, data)

    @async()
    async def test_fetch_paths_output_tomcat_fake_404(self, loop):
        hammertime = HammerTime(loop=loop, request_engine=FakeHammertimeEngine())
        hammertime.heuristics.add(SetResponseCode(404))
        base_url = "http://example.com"
        directory_fetcher = DirectoryFetcher(base_url, hammertime)

        with patch("tachyon.core.textutils.output_found", MagicMock()), \
             patch("tachyon.core.workers.detect_tomcat_fake_404", MagicMock(return_value=True)):
            await directory_fetcher.fetch_paths(self.to_json_data(["/path"]))
            desc = "path"
            data = {
                "description": desc,
                "url": base_url + "/path",
                "code": 404,
                "severity": "warning",
                "special": "tomcat-redirect"
            }
            message = "Tomcat redirect, " + desc + " at: " + base_url + "/path"
            textutils.output_found.assert_called_once_with(message, data)

    def to_json_data(self, path_list):
        data = []
        for path in path_list:
            desc = path[1:]
            data.append({"url": path, "description": desc, "timeout_count": 0, "severity": "warning"})
        return data


class FakeHammertimeEngine:

    async def perform(self, entry, heuristics):
        await heuristics.before_request(entry)
        entry.response = StaticResponse(200, headers={})
        await heuristics.after_headers(entry)
        entry.response.set_content(b"data", at_eof=False)
        await heuristics.after_response(entry)
        return entry


class RaiseForPaths:

    def __init__(self, invalid_paths, exception):
        self.invalid_paths = invalid_paths
        self.exception = exception

    async def before_request(self, entry):
        path = urlparse(entry.request.url).path
        if path in self.invalid_paths:
            raise self.exception


class SetResponseCode:

    def __init__(self, response_code):
        self.response_code = response_code

    async def after_headers(self, entry):
        entry.response.code = self.response_code
