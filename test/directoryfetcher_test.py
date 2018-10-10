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
from unittest.mock import call, patch

from fixtures import async_test, FakeHammerTimeEngine, create_json_data, RaiseForPaths, SetResponseCode, SetFlagInResult
from hammertime.core import HammerTime
from hammertime.ruleset import RejectRequest
from tachyon.database import valid_paths
from tachyon.directoryfetcher import DirectoryFetcher

from tachyon import database


@patch("tachyon.output.OutputManager.output_result")
class TestDirectoryFetcher(TestCase):

    def setUp(self):
        valid_paths.clear()
        self.host = "http://example.com"

    def async_setup(self, loop):
        self.hammertime = HammerTime(loop=loop, request_engine=FakeHammerTimeEngine())
        self.hammertime.collect_successful_requests()
        self.hammertime.heuristics.add_multiple([SetFlagInResult("soft404", False),
                                                 SetFlagInResult("error_behavior", False)])
        self.directory_fetcher = DirectoryFetcher(self.host, self.hammertime)

    @async_test()
    async def test_fetch_paths_add_valid_path_to_database(self, output_result, loop):
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

    @async_test()
    async def test_fetch_paths_dont_add_path_if_response_code_is_401(self, output_result, loop):
        paths = ["/401"]
        self.async_setup(loop)
        self.hammertime.heuristics.add(SetResponseCode(401))

        await self.directory_fetcher.fetch_paths(create_json_data(paths))

        self.assertEqual(len(database.valid_paths), 0)

    @async_test()
    async def test_fetch_paths_output_found_directory(self, output_result, loop):
        found = ["/%d" % i for i in range(10)]
        not_found = ["/1%d" % i for i in range(10)]
        paths = found + not_found
        self.async_setup(loop)
        self.hammertime.heuristics.add(RaiseForPaths(not_found, RejectRequest("404 not found")))

        await self.directory_fetcher.fetch_paths(create_json_data(paths))

        calls = []
        for path in create_json_data(found):
            message, data = self.expected_output(path)
            calls.append(call(message, data=data))
        output_result.assert_has_calls(calls, any_order=True)

    @async_test()
    async def test_fetch_paths_does_not_output_root_path(self, output_result, loop):
        paths = create_json_data(["/"])
        self.async_setup(loop)

        await self.directory_fetcher.fetch_paths(paths)

        self.assertEqual(database.valid_paths, paths)
        output_result.assert_not_called()

    @async_test()
    async def test_fetch_paths_output_401_directory(self, output_result, loop):
        self.async_setup(loop)
        self.hammertime.heuristics.add(SetResponseCode(401))
        path_list = create_json_data(["/admin"])

        await self.directory_fetcher.fetch_paths(path_list)

        message, data = self.expected_output(path_list[0], code=401, message_prefix="Password Protected - ")
        output_result.assert_called_once_with(message, data=data)

    @async_test()
    async def test_fetch_paths_output_500_response(self, output_result, loop):
        self.async_setup(loop)
        self.hammertime.heuristics.add(SetResponseCode(500))
        path_list = create_json_data(["/server-error"])

        await self.directory_fetcher.fetch_paths(path_list)

        message, data = self.expected_output(path_list[0], message_prefix="ISE, ", code=500)
        output_result.assert_called_once_with(message, data=data)

    @async_test()
    async def test_fetch_paths_output_403_directory(self, output_result, loop):
        self.async_setup(loop)
        self.hammertime.heuristics.add(SetResponseCode(403))
        path_list = create_json_data(["/forbidden"])

        await self.directory_fetcher.fetch_paths(path_list)

        message, data = self.expected_output(path_list[0], message_prefix="*Forbidden* ", code=403)
        output_result.assert_called_once_with(message, data=data)

    @async_test()
    async def test_fetch_paths_append_slash_to_path(self, output_result, loop):
        paths = ["/a", "/b", "/c", "/1", "/2", "/3"]
        self.async_setup(loop)
        await self.directory_fetcher.fetch_paths(create_json_data(paths))
        requested = [url for url in self.hammertime.request_engine.request_engine.get_requested_urls()]
        self.assertEqual(len(paths), len(requested))
        for url, path in zip(requested, paths):
            self.assertEqual(url, "{}{}/".format(self.host, path))

    @async_test()
    async def test_fetch_paths_does_not_append_slash_to_root_path(self, output_result, loop):
        paths = ["/"]
        self.async_setup(loop)
        await self.directory_fetcher.fetch_paths(create_json_data(paths))
        requested = list(self.hammertime.request_engine.request_engine.get_requested_urls())[0]
        self.assertEqual(requested, self.host + "/")

    def expected_output(self, path, *, code=200, message_prefix=""):
        url = "{}{}/".format(self.host, path["url"])
        data = {"description": path["description"], "url": url, "severity": path["severity"], "code": code}
        message = "{prefix}{desc} at: {url}".format(prefix=message_prefix, desc=data["description"], url=url)
        return message, data
