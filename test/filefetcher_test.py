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
from unittest.mock import patch, MagicMock, call
from hammertime import HammerTime
from hammertime.http import Entry, StaticResponse
from hammertime.ruleset import StopRequest, RejectRequest

from tachyon.core.filefetcher import FileFetcher
from fixtures import async, create_json_data, FakeHammerTimeEngine, SetResponseCode, fake_future, SetResponseContent,\
    RaiseForPaths
from tachyon.core import database


@patch("tachyon.core.filefetcher.output_found")
class TestFileFetcher(TestCase):

    def setUp(self):
        database.successful_fetch_count = 0

    @async()
    async def test_fetch_files(self, output_found, loop):
        files = ["config", ".htaccess", "data", "files"]
        host = "http://www.example.com"
        hammertime = MagicMock(loop=loop)
        file_fetcher = FileFetcher(host, hammertime)
        file_list = create_json_data(files)
        entries = []
        for file in file_list:
            entry = Entry.create("%s/%s" % (host, file["url"]), response=StaticResponse(200, {}, b"content"),
                                 arguments={"file": file})
            entries.append(fake_future(entry, loop=loop))
        hammertime.request.side_effect = entries

        await file_fetcher.fetch_files(file_list)

        calls = []
        for file in file_list:
            url = "{host}/{file}".format(host=host, file=file["url"])
            calls.append(call(url, arguments={"file": file}))
        hammertime.request.assert_has_calls(calls, any_order=True)

    @async()
    async def test_fetch_files_update_processed_items_if_not_timeout(self, output_found, loop):
        files = ["config", ".htaccess", "data", "files"]
        rejected = ["rejected"]
        timeout_files = ["test"]
        host = "http://www.example.com"
        hammertime = HammerTime(loop=loop, request_engine=FakeHammerTimeEngine())
        hammertime.heuristics.add_multiple([RaiseForPaths(["/test"], StopRequest()),
                                            RaiseForPaths(["/rejected"], RejectRequest())])
        file_fetcher = FileFetcher(host, hammertime)
        file_list = create_json_data(files + timeout_files + rejected)

        await file_fetcher.fetch_files(file_list)

        self.assertEqual(database.successful_fetch_count, len(files + rejected))

    @async()
    async def test_fetch_files_output_found_files(self, output_found, loop):
        file_list = ["config", ".htaccess", "data", "files"]
        host = "http://www.example.com"
        hammertime = HammerTime(loop=loop, request_engine=FakeHammerTimeEngine())
        file_fetcher = FileFetcher(host, hammertime)

        await file_fetcher.fetch_files(create_json_data(file_list))

        calls = []
        for file in file_list:
            url = "{host}/{file}".format(host=host, file=file)
            desc = "description of {file}".format(file=file)
            data = {"description": desc, "url": url, "code": 200, "severity": "warning"}
            calls.append(call("{desc} at: {url}".format(desc=desc, url=url), data=data))
        output_found.assert_has_calls(calls, any_order=True)

    @async()
    async def test_fetch_files_output_responses_with_error_code_500(self, output_found, loop):
        file_list = ["config", ".htaccess"]
        host = "http://www.example.com"
        hammertime = HammerTime(loop=loop, request_engine=FakeHammerTimeEngine())
        hammertime.heuristics.add(SetResponseCode(500))
        file_fetcher = FileFetcher(host, hammertime)

        await file_fetcher.fetch_files(create_json_data(file_list))

        calls = []
        for file in file_list:
            url = "{host}/{file}".format(host=host, file=file)
            desc = "description of {file}".format(file=file)
            data = {"description": desc, "url": url, "code": 500, "severity": "warning"}
            calls.append(call("ISE, {desc} at: {url}".format(desc=desc, url=url), data=data))
        output_found.assert_has_calls(calls, any_order=True)

    @async()
    async def test_fetch_files_output_empty_response(self, output_found, loop):
        file_list = ["empty-file"]
        host = "http://www.example.com"
        hammertime = HammerTime(loop=loop, request_engine=FakeHammerTimeEngine())
        hammertime.heuristics.add(SetResponseContent(b""))
        file_fetcher = FileFetcher(host, hammertime)

        await file_fetcher.fetch_files(create_json_data(file_list))

        file = file_list[0]
        url = "{host}/{file}".format(host=host, file=file)
        desc = "description of {file}".format(file=file)
        data = {"description": desc, "url": url, "code": 200, "severity": "warning"}
        output_found.assert_called_once_with("Empty {desc} at: {url}".format(desc=desc, url=url), data=data)
