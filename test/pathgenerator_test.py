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

from tachyon import database
from tachyon.generator import PathGenerator


class TestPathGenerator(TestCase):

    def setUp(self):
        database.files = []
        database.paths = []
        database.valid_paths = []
        database.path_cache.clear()

    def test_generate_paths_return_paths_from_loaded_file_if_not_using_valid_paths(self):
        database.paths = self.load_paths(["/", "/0", "/1", "/2", "/3", "/4"])
        generator = PathGenerator()

        paths = generator.generate_paths(use_valid_paths=False)

        self.assertEqual(paths, database.paths)

    def test_generate_paths_add_files_with_no_suffixes_to_loaded_paths_if_not_using_valid_paths(self):
        database.paths = self.load_paths(["/", "/0", "/1", "/2"])
        database.files = self.load_files(["file0", "file1", "file2"], no_suffix=False)
        database.files.extend(self.load_files(["index.html", "phpinfo.php"], no_suffix=True))
        generator = PathGenerator()

        paths = generator.generate_paths(use_valid_paths=False)

        self.assertTrue(any(path["url"] == "/file0" for path in paths))
        self.assertTrue(any(path["url"] == "/file1" for path in paths))
        self.assertTrue(any(path["url"] == "/file2" for path in paths))
        self.assertTrue(all(path["url"] != "/index.html" for path in paths))
        self.assertTrue(all(path["url"] != "/php.info" for path in paths))

    def test_generate_paths_append_loaded_paths_to_valid_paths_if_depth_is_one(self):
        paths = ["/", "/0", "/1", "/2", "/3", "/4"]
        database.paths = self.load_paths(paths)
        database.valid_paths = database.paths[:4]
        generator = PathGenerator()

        generated_paths = generator.generate_paths(use_valid_paths=True)

        valid_paths = set(path["url"] for path in database.valid_paths)
        expected_paths = set()
        for path in valid_paths:
            if path != "/":
                expected_paths.update(path + _path for _path in paths if _path != "/")
        self.assertEqual(expected_paths, set(path["url"] for path in generated_paths))

    def test_generate_paths_from_valid_paths_does_not_return_same_path_twice(self):
        paths = ["/0", "/1"]
        database.paths = self.load_paths(paths)
        generator = PathGenerator()

        generated_paths = generator.generate_paths(use_valid_paths=False)
        database.valid_paths.extend(generated_paths)
        generated_paths.extend(generator.generate_paths(use_valid_paths=True))
        database.valid_paths.extend(generated_paths)
        generated_paths.extend(generator.generate_paths(use_valid_paths=True))

        expected_paths = {"/0", "/1", "/0/0", "/0/1", "/1/0", "/1/1"}
        temp = []
        for path in expected_paths:
            for _path in paths:
                temp.append(path + _path)
        expected_paths.update(path for path in temp)
        self.assertEqual(len(expected_paths), len(generated_paths))
        self.assertTrue(all(path["url"] in expected_paths for path in generated_paths))
        self.assertFalse(any(path["url"] not in expected_paths for path in generated_paths))

    def load_paths(self, path_list):
        loaded_paths = []
        for path in path_list:
            _path = {"url": path, "description": "desc", "timeout_count": 0, "severity": "warning"}
            loaded_paths.append(_path)
        return loaded_paths

    def load_files(self, file_list, no_suffix=False):
        loaded_files = []
        for filename in file_list:
            file = {"url": filename, "description": "desc", "severity": "warning", "timeout_count": 0,
                    "no_suffix": no_suffix}
            loaded_files.append(file)
        return loaded_files
