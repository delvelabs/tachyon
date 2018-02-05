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
from aiohttp.test_utils import make_mocked_coro
import importlib.util
import asyncio
from hammertime.rules import RejectStatusCode

from tachyon.core import conf, database
spec = importlib.util.spec_from_file_location("tachyon", "/home/nicolas/tachyon/tachyon.py")
tachyon = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tachyon)


class TestTachyon(TestCase):

    def setUp(self):
        conf.recursive = False
        tachyon.DetectSoft404 = RejectStatusCode  # Else adding heuristic using kb more than once would raise exception.

    def test_paths_exists_fetch_generated_paths(self):
        path_generator = MagicMock()
        path_generator.generate_paths.return_value = ["/", "/test", "/path"]
        fake_directory_fetcher = MagicMock()
        fake_directory_fetcher.fetch_paths = make_mocked_coro()
        tachyon.PathGenerator = MagicMock(return_value=path_generator)
        tachyon.DirectoryFetcher = MagicMock(return_value=fake_directory_fetcher)
        asyncio.set_event_loop(asyncio.new_event_loop())

        tachyon.test_paths_exists()

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
            tachyon.test_paths_exists()

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

        tachyon.test_paths_exists()

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
            tachyon.test_paths_exists()

            output_info.assert_any_call("Found %d valid paths" % len(database.valid_paths))
