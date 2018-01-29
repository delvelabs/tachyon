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
from unittest.mock import MagicMock
from hammertime.core import HammerTime
from hammertime.ruleset import RejectRequest, StopRequest
from hammertime.http import StaticResponse
from urllib.parse import urlparse

from core import database
from core.database import valid_paths
from core.directoryfetcher import DirectoryFetcher
from fixtures import async


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
        found = []
        not_found = []
        paths = found + not_found


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
