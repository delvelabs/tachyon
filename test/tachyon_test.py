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
from unittest.mock import MagicMock, patch, call
from aiohttp.test_utils import make_mocked_coro, loop_context
import asyncio
from hammertime.rules import RejectStatusCode
from hammertime.core import HammerTime
from hammertime.http import Entry, StaticResponse

from tachyon.core import conf, database
from tachyon import __main__ as tachyon
from fixtures import fake_future


def patch_stuff(func):
    def wrapper(self):
        with patch("tachyon.__main__.test_file_exists"), patch("tachyon.__main__test_paths_exists"):
            func(self)
    return wrapper


class TestTachyon(TestCase):

    def setUp(self):
        conf.recursive = False
        tachyon.DetectSoft404 = RejectStatusCode  # Else adding heuristic using kb more than once would raise exception.
        self.hammertime = MagicMock(loop=asyncio.new_event_loop())
        tachyon.load_execute_file_plugins = MagicMock()
        database.messages_output_queue = MagicMock()

    def test_paths_exists_fetch_generated_paths(self):
        path_generator = MagicMock()
        path_generator.generate_paths.return_value = ["/", "/test", "/path"]
        fake_directory_fetcher = MagicMock()
        fake_directory_fetcher.fetch_paths = make_mocked_coro()
        tachyon.PathGenerator = MagicMock(return_value=path_generator)
        tachyon.DirectoryFetcher = MagicMock(return_value=fake_directory_fetcher)
        asyncio.set_event_loop(asyncio.new_event_loop())

        tachyon.test_paths_exists(self.hammertime)

        fake_directory_fetcher.fetch_paths.assert_called_once_with(path_generator.generate_paths.return_value)

    def test_paths_exists_output_fetch_paths_count(self):
        path_generator = MagicMock()
        paths = ["/", "/test", "/path"]
        path_generator.generate_paths.return_value = paths
        fake_directory_fetcher = MagicMock()
        fake_directory_fetcher.fetch_paths = make_mocked_coro()
        tachyon.PathGenerator = MagicMock(return_value=path_generator)
        tachyon.DirectoryFetcher = MagicMock(return_value=fake_directory_fetcher)
        asyncio.set_event_loop(asyncio.new_event_loop())

        with patch("tachyon.core.textutils.output_info") as output_info:
            tachyon.test_paths_exists(self.hammertime)

            output_info.assert_any_call("Probing %d paths" % len(paths))

    def test_paths_exists_do_recursive_path_search_if_recursive_is_true(self):
        conf.recursive = True
        path_generator = MagicMock()
        paths = ["/", "/test", "/path"]
        path_generator.generate_paths.return_value = paths
        fake_directory_fetcher = MagicMock()
        fake_directory_fetcher.fetch_paths = make_mocked_coro()
        tachyon.PathGenerator = MagicMock(return_value=path_generator)
        tachyon.DirectoryFetcher = MagicMock(return_value=fake_directory_fetcher)
        asyncio.set_event_loop(asyncio.new_event_loop())

        tachyon.test_paths_exists(self.hammertime)

        path_generator.generate_paths.assert_has_calls([call(use_valid_paths=False), call(use_valid_paths=True),
                                                        call(use_valid_paths=True)], any_order=False)

        fake_directory_fetcher.fetch_paths.assert_has_calls([call(paths)]*3)

    def test_paths_exists_output_paths_found_count(self):
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
            tachyon.test_paths_exists(self.hammertime)

            output_info.assert_any_call("Found %d valid paths" % len(database.valid_paths))

    def test_file_exists_fetch_all_generate_files(self):
        database.valid_paths = ["/path/file%d" % i for i in range(10)]
        fake_file_fetcher = MagicMock()
        fake_file_fetcher.fetch_files = make_mocked_coro()
        tachyon.FileFetcher = MagicMock(return_value=fake_file_fetcher)
        loop = asyncio.new_event_loop()
        hammertime = MagicMock(loop=loop)
        fake_file_generator = MagicMock()
        fake_file_generator.generate_files.return_value = ["list of files"]

        with patch("tachyon.__main__.FileGenerator", MagicMock(return_value=fake_file_generator)):
            tachyon.test_file_exists(hammertime)

        fake_file_fetcher.fetch_files.assert_called_once_with(["list of files"])

    @patch_stuff
    def test_fetch_session_cookies_on_scan_start(self):
        tachyon.configure_hammertime = MagicMock(return_value=self.hammertime)
        with patch("tachyon.__main__.get_session_cookies", make_mocked_coro()) as get_session_cookies:
            tachyon.scan()

            get_session_cookies.assert_called_once_with(self.hammertime)

    def test_get_session_cookies(self):
        conf.base_url = "http://example.com"
        database.session_cookie = None
        with loop_context() as loop:
            hammertime = HammerTime(loop=loop)
            response = StaticResponse(200, {"Set-Cookie": "my-cookie=true; test-cookie=123"})
            entry = Entry.create("http://example.com/", response=response)
            hammertime.request = MagicMock(return_value=fake_future(result=entry, loop=loop))

            loop.run_until_complete(tachyon.get_session_cookies(hammertime))

            hammertime.request.assert_called_once_with("http://example.com/")
            self.assertEqual(database.session_cookie, "my-cookie=true; test-cookie=123")

    def test_get_session_cookies_skip_if_no_cookies_in_response(self):
        conf.base_url = "http://example.com"
        database.session_cookie = None
        with loop_context() as loop:
            hammertime = HammerTime(loop=loop)
            response = StaticResponse(200, {"No-Set-Cookie": "lorem ipsum"})
            entry = Entry.create("http://example.com/", response=response)
            hammertime.request = MagicMock(return_value=fake_future(result=entry, loop=loop))

            loop.run_until_complete(tachyon.get_session_cookies(hammertime))

            hammertime.request.assert_called_once_with("http://example.com/")
            self.assertIsNone(database.session_cookie)

    @patch_stuff
    def test_hammertime_uses_session_cookies(self):
        tachyon.configure_hammertime = MagicMock(return_value=self.hammertime)
        database.session_cookie = "my-cookies=123"
        with patch("tachyon.__main__.get_session_cookies", make_mocked_coro()):
            tachyon.scan()

        set_header = self.hammertime.heuristics.add.call_args[0][0]
        self.assertEqual(set_header.name, "Cookie")
        self.assertEqual(set_header.value, database.session_cookie)

    @patch_stuff
    def test_dont_set_cookies_if_database_session_cookies_is_none(self):
        tachyon.configure_hammertime = MagicMock(return_value=self.hammertime)
        database.session_cookie = None
        with patch("tachyon.__main__.get_session_cookies", make_mocked_coro()):
            tachyon.scan()

        self.hammertime.heuristics.add.assert_not_called()
