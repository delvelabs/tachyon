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
from unittest.mock import patch, MagicMock, call

from fixtures import async, create_json_data, FakeHammerTimeEngine, SetResponseCode, fake_future, SetResponseContent, \
    SetFlagInResult
from hammertime import HammerTime
from hammertime.http import Entry, StaticResponse
from hammertime.kb import KnowledgeBase

from tachyon import conf
from tachyon.config import setup_hammertime_heuristics
from tachyon.filefetcher import FileFetcher


@patch("tachyon.filefetcher.output_found")
class TestFileFetcher(TestCase):

    def setUp(self):
        self.host = "http://www.example.com"
        self.files = create_json_data(["config", ".htaccess", "data", "files"])

    def setUpFetcher(self, loop):
        self.hammertime = HammerTime(loop=loop, request_engine=FakeHammerTimeEngine(), kb=KnowledgeBase())
        conf.target_host = self.host
        self.file_fetcher = FileFetcher(self.host, self.hammertime)

    def setup_hammertime_heuristics(self, add_before_defaults=None, add_after_defaults=None):
        if add_before_defaults is not None:
            self.hammertime.heuristics.add_multiple(add_before_defaults)
        with patch("tachyon.config.DetectSoft404", new=MagicMock(return_value=SetFlagInResult("soft404", False))):
            setup_hammertime_heuristics(self.hammertime)
        if add_after_defaults is not None:
            self.hammertime.heuristics.add_multiple(add_after_defaults)

    @classmethod
    def setUpClass(cls):
        cls.patcher = patch("tachyon.textutils.output_manager")
        cls.patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.patcher.stop()

    @async()
    async def test_fetch_files_makes_hammertime_requests_for_files(self, output_found, loop):
        hammertime = MagicMock(loop=loop)
        file_fetcher = FileFetcher(self.host, hammertime)
        file_fetcher._is_entry_invalid = MagicMock(return_value=False)
        entries = []
        for file in self.files:
            entry = Entry.create("%s/%s" % (self.host, file["url"]), response=StaticResponse(200, {}, "content"),
                                 arguments={"file": file})
            entries.append(fake_future(entry, loop=loop))
        hammertime.request.side_effect = entries

        await file_fetcher.fetch_files(self.files)

        calls = []
        for file in self.files:
            url = "{host}/{file}".format(host=self.host, file=file["url"])
            calls.append(call(url, arguments={"file": file}))
        hammertime.request.assert_has_calls(calls, any_order=True)

    @async()
    async def test_fetch_files_output_found_files(self, output_found, loop):
        self.setUpFetcher(loop)
        self.setup_hammertime_heuristics()

        await self.file_fetcher.fetch_files(self.files)

        calls = []
        for file in self.files:
            calls.append(self.to_output_found_call(file))
        output_found.assert_has_calls(calls, any_order=True)

    @async()
    async def test_fetch_files_output_responses_with_error_code_500(self, output_found, loop):
        file_list = create_json_data(["config", ".htaccess"])
        self.setUpFetcher(loop)
        self.setup_hammertime_heuristics(add_before_defaults=[SetResponseCode(500)])

        await self.file_fetcher.fetch_files(file_list)

        calls = []
        for file in file_list:
            calls.append(self.to_output_found_call(file, prefix="ISE, ", status_code=500))
        output_found.assert_has_calls(calls, any_order=True)

    @async()
    async def test_fetch_files_output_empty_response(self, output_found, loop):
        file_list = create_json_data(["empty-file"])
        self.setUpFetcher(loop)
        self.setup_hammertime_heuristics(add_after_defaults=[SetResponseContent("")])

        await self.file_fetcher.fetch_files(file_list)

        file = file_list[0]
        call = self.to_output_found_call(file, "Empty ")
        output_found.assert_has_calls([call])

    @async()
    async def test_fetch_files_do_not_output_redirects(self, output_found, loop):
        files = ["/admin/resource", "/admin/file"]
        self.setUpFetcher(loop)
        self.setup_hammertime_heuristics(add_before_defaults=[SetResponseCode(302)])

        await self.file_fetcher.fetch_files(create_json_data(files))

        output_found.assert_not_called()

    @async()
    async def test_fetch_files_reject_soft_404(self, output_found, loop):
        file = create_json_data(["file"])[0]
        self.setUpFetcher(loop)
        self.setup_hammertime_heuristics()
        self.setup_hammertime_heuristics(add_after_defaults=[SetFlagInResult("soft404", True)])

        await self.file_fetcher.fetch_files([file])

        output_found.assert_not_called()

    @async()
    async def test_fetch_files_do_not_reject_soft_404_if_string_match_is_true(self, output_found, loop):
        file = create_json_data(["file"])[0]
        self.setUpFetcher(loop)
        self.setup_hammertime_heuristics(add_before_defaults=[SetFlagInResult("soft404", True),
                                                              SetFlagInResult("string_match", True)])

        await self.file_fetcher.fetch_files([file])

        output_found.assert_has_calls([self.to_output_found_call(file)])

    @async()
    async def test_fetch_files_do_not_reject_behavior_error_if_string_match_is_true(self, output_found, loop):
        file = create_json_data(["file"])[0]
        self.setUpFetcher(loop)
        set_error_behavior = SetFlagInResult("error_behavior", True)
        with patch("tachyon.config.DetectBehaviorChange", new=MagicMock(return_value=set_error_behavior)):
            self.setup_hammertime_heuristics(add_after_defaults=[SetFlagInResult("string_match", True)])

        await self.file_fetcher.fetch_files([file])

        output_found.assert_has_calls([self.to_output_found_call(file)])

    @async()
    async def test_fetch_files_reject_error_behavior(self, output_found, loop):
        file = create_json_data(["file"])[0]
        self.setUpFetcher(loop)
        set_error_behavior = SetFlagInResult("error_behavior", True)
        with patch("tachyon.config.DetectBehaviorChange", new=MagicMock(return_value=set_error_behavior)):
            self.setup_hammertime_heuristics()

        await self.file_fetcher.fetch_files([file])

        output_found.assert_not_called()

    def to_output_found_call(self, file, prefix="", status_code=200):
        url = "{host}/{file}".format(host=self.host, file=file["url"])
        desc = "description of {file}".format(file=file["url"])
        data = {"description": desc, "url": url, "code": status_code, "severity": "warning"}
        return call("{prefix}{desc} at: {url}".format(prefix=prefix, desc=desc, url=url), data=data)
