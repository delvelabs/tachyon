# Tachyon - Fast Multi-Threaded Web Discovery Tool
# Copyright (c) 2011 Gabriel Tremblay - initnull hat gmail.com
# Copyright (C) 2018-  Delve Labs inc.
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

from fixtures import async, FakeHammerTimeEngine, create_json_data, RaiseForPaths, SetResponseCode, SetFlagInResult
from hammertime.core import HammerTime
from hammertime.ruleset import RejectRequest
from tachyon.database import valid_paths
from tachyon.directoryfetcher import DirectoryFetcher

from tachyon import textutils
from tachyon import database


class TestDirectoryFetcher(TestCase):

    def setUp(self):
        valid_paths.clear()
        self.host = "http://example.com"
        self.fake_output = patch("tachyon.textutils.output_found")
        self.fake_output.start()

    def tearDown(self):
        self.fake_output.stop()

    def async_setup(self, loop):
        self.hammertime = HammerTime(loop=loop, request_engine=FakeHammerTimeEngine())
        self.hammertime.heuristics.add_multiple([SetFlagInResult("soft404", False),
                                                 SetFlagInResult("error_behavior", False)])
        self.directory_fetcher = DirectoryFetcher(self.host, self.hammertime)

    @async()
    async def test_fetch_paths_add_valid_path_to_database(self, loop):
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
    async def test_fetch_paths_dont_add_path_if_response_code_is_401(self, loop):
        paths = ["/401"]
        self.async_setup(loop)
        self.hammertime.heuristics.add(SetResponseCode(401))

        await self.directory_fetcher.fetch_paths(create_json_data(paths))

        self.assertEqual(len(database.valid_paths), 0)

    @async()
    async def test_fetch_paths_output_found_directory(self, loop):
        found = ["/%d" % i for i in range(10)]
        not_found = ["/1%d" % i for i in range(10)]
        paths = found + not_found
        self.async_setup(loop)
        self.hammertime.heuristics.add(RaiseForPaths(not_found, RejectRequest("404 not found")))

        await self.directory_fetcher.fetch_paths(create_json_data(paths))

        calls = []
        for path in create_json_data(found):
            message, data = self.expected_output(path)
            calls.append(call(message, data))
        textutils.output_found.assert_has_calls(calls, any_order=True)

    @async()
    async def test_fetch_paths_does_not_output_root_path(self, loop):
        paths = create_json_data(["/"])
        self.async_setup(loop)

        await self.directory_fetcher.fetch_paths(paths)

        self.assertEqual(database.valid_paths, paths)
        textutils.output_found.assert_not_called()

    @async()
    async def test_fetch_paths_output_401_directory(self, loop):
        self.async_setup(loop)
        self.hammertime.heuristics.add(SetResponseCode(401))
        path_list = create_json_data(["/admin"])

        await self.directory_fetcher.fetch_paths(path_list)

        message, data = self.expected_output(path_list[0], code=401, message_prefix="Password Protected - ")
        textutils.output_found.assert_called_once_with(message, data)

    @async()
    async def test_fetch_paths_output_500_response(self, loop):
        self.async_setup(loop)
        self.hammertime.heuristics.add(SetResponseCode(500))
        path_list = create_json_data(["/server-error"])

        await self.directory_fetcher.fetch_paths(path_list)

        message, data = self.expected_output(path_list[0], message_prefix="ISE, ", code=500)
        textutils.output_found.assert_called_once_with(message, data)

    @async()
    async def test_fetch_paths_output_403_directory(self, loop):
        self.async_setup(loop)
        self.hammertime.heuristics.add(SetResponseCode(403))
        path_list = create_json_data(["/forbidden"])

        await self.directory_fetcher.fetch_paths(path_list)

        message, data = self.expected_output(path_list[0], message_prefix="*Forbidden* ", code=403)
        textutils.output_found.assert_called_once_with(message, data)

    @async()
    async def test_fetch_paths_output_tomcat_fake_404(self, loop):
        self.async_setup(loop)
        self.hammertime.heuristics.add(SetResponseCode(404))
        path_list = create_json_data(["/path"])
        self.directory_fetcher.detect_tomcat_fake_404 = MagicMock(return_value=True)

        await self.directory_fetcher.fetch_paths(path_list)

        message, data = self.expected_output(path_list[0], message_prefix="Tomcat redirect, ", code=404)
        data["special"] = "tomcat-redirect"
        textutils.output_found.assert_called_once_with(message, data)

    @async()
    async def test_fetch_paths_append_slash_to_path(self, loop):
        paths = ["/a", "/b", "/c", "/1", "/2", "/3"]
        self.async_setup(loop)
        await self.directory_fetcher.fetch_paths(create_json_data(paths))
        requested = [url for url in self.hammertime.request_engine.request_engine.get_requested_urls()]
        self.assertEqual(len(paths), len(requested))
        for url, path in zip(requested, paths):
            self.assertEqual(url, "{}{}/".format(self.host, path))

    @async()
    async def test_fetch_paths_does_not_append_slash_to_root_path(self, loop):
        paths = ["/"]
        self.async_setup(loop)
        await self.directory_fetcher.fetch_paths(create_json_data(paths))
        requested = list(self.hammertime.request_engine.request_engine.get_requested_urls())[0]
        self.assertEqual(requested, self.host + "/")

    @async()
    async def test_fetch_paths_ignore_soft404(self, loop):
        self.async_setup(loop)
        self.hammertime.heuristics.add(SetFlagInResult("soft404", True))

        await self.directory_fetcher.fetch_paths(create_json_data(["path"]))

        textutils.output_found.assert_not_called()

    @async()
    async def test_fetch_paths_ignore_behavior_error(self, loop):
        self.async_setup(loop)
        self.hammertime.heuristics.add(SetFlagInResult("error_behavior", True))

        await self.directory_fetcher.fetch_paths(create_json_data(["path"]))

        textutils.output_found.assert_not_called()

    def expected_output(self, path, *, code=200, message_prefix=""):
        url = "{}{}/".format(self.host, path["url"])
        data = {"description": path["description"], "url": url, "severity": path["severity"], "code": code}
        message = "{prefix}{desc} at: {url}".format(prefix=message_prefix, desc=data["description"], url=url)
        return message, data
