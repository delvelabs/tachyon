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
from unittest.mock import MagicMock, patch, call, ANY
from aiohttp.test_utils import make_mocked_coro
import asyncio
from hammertime.rules import RejectCatchAllRedirect, FollowRedirects
from hammertime.core import HammerTime
from hammertime.http import Entry, StaticResponse

from tachyon.core import conf, database
from tachyon import __main__ as tachyon
from fixtures import fake_future, async, patch_coroutines


class TestTachyon(TestCase):

    def setUp(self):
        conf.recursive = False
        tachyon.load_execute_file_plugins = MagicMock()
        database.messages_output_queue = MagicMock()

    @async()
    async def test_paths_exists_fetch_generated_paths(self, loop):
        path_generator = MagicMock()
        path_generator.generate_paths.return_value = ["/", "/test", "/path"]
        fake_directory_fetcher = MagicMock()
        fake_directory_fetcher.fetch_paths = make_mocked_coro()
        tachyon.PathGenerator = MagicMock(return_value=path_generator)
        tachyon.DirectoryFetcher = MagicMock(return_value=fake_directory_fetcher)

        await tachyon.test_paths_exists(HammerTime(loop=loop))

        fake_directory_fetcher.fetch_paths.assert_called_once_with(path_generator.generate_paths.return_value)

    @async()
    async def test_paths_exists_output_fetch_paths_count(self, loop):
        path_generator = MagicMock()
        paths = ["/", "/test", "/path"]
        path_generator.generate_paths.return_value = paths
        fake_directory_fetcher = MagicMock()
        fake_directory_fetcher.fetch_paths = make_mocked_coro()
        tachyon.PathGenerator = MagicMock(return_value=path_generator)
        tachyon.DirectoryFetcher = MagicMock(return_value=fake_directory_fetcher)

        with patch("tachyon.core.textutils.output_info") as output_info:
            await tachyon.test_paths_exists(HammerTime(loop=loop))

            output_info.assert_any_call("Probing %d paths" % len(paths))

    @async()
    async def test_paths_exists_do_recursive_path_search_if_recursive_is_true(self, loop):
        conf.recursive = True
        path_generator = MagicMock()
        paths = ["/", "/test", "/path"]
        path_generator.generate_paths.return_value = paths
        fake_directory_fetcher = MagicMock()
        fake_directory_fetcher.fetch_paths = make_mocked_coro()
        tachyon.PathGenerator = MagicMock(return_value=path_generator)
        tachyon.DirectoryFetcher = MagicMock(return_value=fake_directory_fetcher)

        await tachyon.test_paths_exists(HammerTime(loop=loop))

        path_generator.generate_paths.assert_has_calls([call(use_valid_paths=False), call(use_valid_paths=True),
                                                        call(use_valid_paths=True)], any_order=False)

        fake_directory_fetcher.fetch_paths.assert_has_calls([call(paths)]*3)

    @async()
    async def test_paths_exists_output_paths_found_count(self, loop):
        path_generator = MagicMock()
        paths = ["/", "/test", "/path"]
        path_generator.generate_paths.return_value = paths
        fake_directory_fetcher = MagicMock()
        fake_directory_fetcher.fetch_paths = make_mocked_coro()
        tachyon.PathGenerator = MagicMock(return_value=path_generator)
        tachyon.DirectoryFetcher = MagicMock(return_value=fake_directory_fetcher)
        asyncio.set_event_loop(asyncio.new_event_loop())
        database.valid_paths = paths

        with patch("tachyon.core.textutils.output_info") as output_info:
            await tachyon.test_paths_exists(HammerTime(loop=loop))

            output_info.assert_any_call("Found %d valid paths" % len(database.valid_paths))

    @async()
    async def test_file_exists_fetch_all_generate_files(self, loop):
        database.valid_paths = ["/path/file%d" % i for i in range(10)]
        fake_file_fetcher = MagicMock()
        fake_file_fetcher.fetch_files = make_mocked_coro()
        tachyon.FileFetcher = MagicMock(return_value=fake_file_fetcher)
        fake_file_generator = MagicMock()
        fake_file_generator.generate_files.return_value = ["list of files"]

        with patch("tachyon.__main__.FileGenerator", MagicMock(return_value=fake_file_generator)):
            await tachyon.test_file_exists(HammerTime(loop=loop))

        fake_file_fetcher.fetch_files.assert_called_once_with(["list of files"])

    @async()
    async def test_add_http_headers(self, loop):
        hammertime = HammerTime(loop=loop)
        tachyon.heuristics_with_child = [RejectCatchAllRedirect(), FollowRedirects()]
        hammertime.heuristics.add_multiple(tachyon.heuristics_with_child)
        hammertime.heuristics.add = MagicMock()
        for heuristic in tachyon.heuristics_with_child:
            heuristic.child_heuristics.add = MagicMock()

        tachyon.add_http_header(hammertime, "header", "value")

        set_header = hammertime.heuristics.add.call_args[0][0]
        self.assertEqual(set_header.name, "header")
        self.assertEqual(set_header.value, "value")
        for heuristic_with_child in tachyon.heuristics_with_child:
            set_header = heuristic_with_child.child_heuristics.add.call_args[0][0]
            self.assertEqual(set_header.name, "header")
            self.assertEqual(set_header.value, "value")

    @patch_coroutines("tachyon.__main__.", "test_file_exists", "test_paths_exists", "get_session_cookies")
    @async()
    async def test_fetch_session_cookies_on_scan_start(self):
        hammertime = MagicMock()

        await tachyon.scan(hammertime)

        tachyon.get_session_cookies.assert_called_once_with(hammertime)

    @async()
    async def test_get_session_cookies(self, loop):
        conf.base_url = "http://example.com"
        database.session_cookie = None
        hammertime = HammerTime(loop=loop)
        response = StaticResponse(200, {"Set-Cookie": "my-cookie=true; test-cookie=123"})
        entry = Entry.create("http://example.com/", response=response)
        hammertime.request = MagicMock(return_value=fake_future(result=entry, loop=loop))

        await tachyon.get_session_cookies(hammertime)

        hammertime.request.assert_called_once_with("http://example.com/")
        self.assertEqual(database.session_cookie, "my-cookie=true; test-cookie=123")

    @async()
    async def test_get_session_cookies_leave_session_cookies_to_none_if_no_cookies_in_response(self, loop):
        conf.base_url = "http://example.com"
        database.session_cookie = None
        hammertime = HammerTime(loop=loop)
        response = StaticResponse(200, {"No-Set-Cookie": "lorem ipsum"})
        entry = Entry.create("http://example.com/", response=response)
        hammertime.request = MagicMock(return_value=fake_future(result=entry, loop=loop))

        await tachyon.get_session_cookies(hammertime)

        hammertime.request.assert_called_once_with("http://example.com/")
        self.assertIsNone(database.session_cookie)

    @patch_coroutines("tachyon.__main__.", "test_file_exists", "test_paths_exists", "get_session_cookies")
    @async()
    async def test_hammertime_uses_session_cookies(self, loop):
        hammertime = HammerTime(loop=loop)
        tachyon.add_http_header = MagicMock()
        database.session_cookie = "my-cookies=123"

        await tachyon.scan(hammertime)

        tachyon.add_http_header.assert_called_once_with(ANY, "Cookie", "my-cookies=123")

    @patch_coroutines("tachyon.__main__.", "test_file_exists", "test_paths_exists", "get_session_cookies")
    @async()
    async def test_dont_set_cookies_if_database_session_cookies_is_none(self):
        hammertime = MagicMock()
        database.session_cookie = None

        await tachyon.scan(hammertime)

        hammertime.heuristics.add.assert_not_called()

    @patch_coroutines("tachyon.__main__.", "test_file_exists", "test_paths_exists", "get_session_cookies")
    @async()
    async def test_use_user_supplied_cookies_if_available(self, loop):
        hammertime = HammerTime(loop=loop)
        tachyon.add_http_header = MagicMock()
        database.session_cookie = "my-cookies=123"
        conf.cookies = "test-cookie=true"

        await tachyon.scan(hammertime)

        tachyon.add_http_header.assert_called_once_with(ANY, "Cookie", "test-cookie=true")

    @async()
    async def test_configure_hammertime_add_user_agent_to_request_header(self):
        conf.user_agent = "My-user-agent"
        tachyon.add_http_header = MagicMock()

        tachyon.configure_hammertime()

        tachyon.add_http_header.assert_any_call(ANY, "User-Agent", conf.user_agent)

    @async()
    async def test_configure_hammertime_add_connection_header_to_request_header(self):
        tachyon.add_http_header = MagicMock()

        with patch("tachyon.__main__.HammerTime"):
            tachyon.configure_hammertime()

            tachyon.add_http_header.assert_any_call(ANY, "Connection", "Keep-Alive")

    @async()
    async def test_configure_hammertime_add_host_header_to_request_header(self):
        conf.target_host = "example.com"
        tachyon.add_http_header = MagicMock()

        with patch("tachyon.__main__.HammerTime"):
            tachyon.configure_hammertime()

            tachyon.add_http_header.assert_any_call(ANY, "Host", conf.target_host)
