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


import asyncio
from unittest import TestCase
from unittest.mock import MagicMock, patch, call, ANY

from aiohttp.test_utils import make_mocked_coro
from fixtures import async, patch_coroutines
from hammertime.core import HammerTime

from tachyon import __main__ as tachyon, database


class TestTachyon(TestCase):

    def setUp(self):
        tachyon.load_execute_file_plugins = MagicMock()
        tachyon.load_execute_host_plugins = make_mocked_coro()

    @classmethod
    def setUpClass(cls):
        cls.patcher = patch("tachyon.textutils.output_manager")
        cls.patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.patcher.stop()

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

        with patch("tachyon.textutils.output_info") as output_info:
            await tachyon.test_paths_exists(HammerTime(loop=loop))

            output_info.assert_any_call("Probing %d paths" % len(paths))

    @async()
    async def test_paths_exists_do_recursive_path_search_if_recursive_is_true(self, loop):
        path_generator = MagicMock()
        paths = ["/", "/test", "/path"]
        path_generator.generate_paths.return_value = paths
        fake_directory_fetcher = MagicMock()
        fake_directory_fetcher.fetch_paths = make_mocked_coro()
        tachyon.PathGenerator = MagicMock(return_value=path_generator)
        tachyon.DirectoryFetcher = MagicMock(return_value=fake_directory_fetcher)

        await tachyon.test_paths_exists(HammerTime(loop=loop), recursive=True)

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

        with patch("tachyon.textutils.output_info") as output_info:
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

    @patch_coroutines("tachyon.__main__.", "test_file_exists", "test_paths_exists", "get_session_cookies")
    @async()
    async def test_fetch_session_cookies_on_scan_start_if_no_user_supplied_cookies(self):
        hammertime = MagicMock()

        await tachyon.scan(hammertime, cookies=None)

        tachyon.get_session_cookies.assert_called_once_with(hammertime)

    @patch_coroutines("tachyon.__main__.", "test_file_exists", "test_paths_exists", "get_session_cookies")
    @async()
    async def test_dont_fetch_session_cookies_on_scan_start_if_user_supplied_cookies(self):
        hammertime = MagicMock()
        cookies = "not none"

        await tachyon.scan(hammertime, cookies=cookies)

        tachyon.get_session_cookies.assert_not_called()

    @async()
    async def test_use_user_supplied_cookies_if_available(self):
        database.session_cookie = "my-cookies=123"
        cookies = "test-cookie=true"
        hammertime = MagicMock()

        with patch("tachyon.config.add_http_header") as add_http_header:
            await tachyon.scan(hammertime, cookies=cookies)

            add_http_header.assert_any_call(ANY, "Cookie", "test-cookie=true")

    @patch_coroutines("tachyon.__main__.", "test_file_exists", "test_paths_exists", "get_session_cookies")
    @async()
    async def test_scan_directory_only(self):
        hammertime = MagicMock()

        await tachyon.scan(hammertime, directories_only=True)

        tachyon.test_paths_exists.assert_called_once_with(hammertime)
        tachyon.test_file_exists.assert_not_called()

    @patch_coroutines("tachyon.__main__.", "test_file_exists", "test_paths_exists", "get_session_cookies")
    @async()
    async def test_scan_file_only(self):
        hammertime = MagicMock()

        await tachyon.scan(hammertime, files_only=True)

        tachyon.test_file_exists.assert_called_once_with(hammertime)
        tachyon.test_paths_exists.assert_not_called()

    @patch_coroutines("tachyon.__main__.", "test_file_exists", "test_paths_exists", "get_session_cookies")
    @async()
    async def test_scan_plugins_only(self):
        hammertime = MagicMock()

        await tachyon.scan(hammertime, plugins_only=True)

        tachyon.load_execute_host_plugins.assert_called_once_with(hammertime)
        tachyon.test_file_exists.assert_not_called()
        tachyon.test_paths_exists.assert_not_called()
