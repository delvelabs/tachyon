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

from tachyon.core import database
from tachyon.core.generator import PathGenerator, FileGenerator
from tachyon.core import conf


class TestPathGenerator(TestCase):

    def setUp(self):
        database.files = []
        database.paths = []
        database.valid_paths = []
        database.path_cache.clear()
        self.generator = PathGenerator()

    def test_generate_paths_return_paths_from_loaded_file_if_not_using_valid_paths(self):
        database.paths = load_paths(["/", "/0", "/1", "/2", "/3", "/4"])

        paths = self.generator.generate_paths(use_valid_paths=False)

        self.assertEqual(paths, database.paths)

    def test_generate_paths_add_files_with_no_suffixes_to_loaded_paths_if_not_using_valid_paths(self):
        database.paths = load_paths(["/", "/0", "/1", "/2"])
        database.files = load_files(["file0", "file1", "file2"], no_suffix=False)
        database.files.extend(load_files(["index.html", "phpinfo.php"], no_suffix=True))

        paths = self.generator.generate_paths(use_valid_paths=False)

        self.assertTrue(any(path["url"] == "/file0" for path in paths))
        self.assertTrue(any(path["url"] == "/file1" for path in paths))
        self.assertTrue(any(path["url"] == "/file2" for path in paths))
        self.assertTrue(all(path["url"] != "/index.html" for path in paths))
        self.assertTrue(all(path["url"] != "/php.info" for path in paths))

    def test_generate_paths_append_loaded_paths_to_valid_paths_if_depth_is_one(self):
        paths = ["/", "/0", "/1", "/2", "/3", "/4"]
        database.paths = load_paths(paths)
        database.valid_paths = database.paths[:4]

        generated_paths = self.generator.generate_paths(use_valid_paths=True)

        valid_paths = set(path["url"] for path in database.valid_paths)
        expected_paths = set()
        for path in valid_paths:
            if path != "/":
                expected_paths.update(path + _path for _path in paths if _path != "/")
        self.assertEqual(expected_paths, set(path["url"] for path in generated_paths))

    def test_generate_paths_from_valid_paths_does_not_return_same_path_twice(self):
        paths = ["/0", "/1"]
        database.paths = load_paths(paths)

        generated_paths = self.generator.generate_paths(use_valid_paths=False)
        database.valid_paths.extend(generated_paths)
        generated_paths.extend(self.generator.generate_paths(use_valid_paths=True))
        database.valid_paths.extend(generated_paths)
        generated_paths.extend(self.generator.generate_paths(use_valid_paths=True))

        expected_paths = {"/0", "/1", "/0/0", "/0/1", "/1/0", "/1/1"}
        temp = []
        for path in expected_paths:
            for _path in paths:
                temp.append(path + _path)
        expected_paths.update(path for path in temp)
        self.assertEqual(len(expected_paths), len(generated_paths))
        self.assertTrue(all(path["url"] in expected_paths for path in generated_paths))
        self.assertFalse(any(path["url"] not in expected_paths for path in generated_paths))


class TestFileGenerator(TestCase):

    def setUp(self):
        self.generator = FileGenerator()

    def test_generate_file_append_loaded_files_to_valid_path_if_no_suffix(self):
        database.valid_paths = load_paths(["/", "/0", "/1/", "2"])
        database.files = load_files(["/abc.html", "/123.php", "test"], no_suffix=True)

        files = self.generator.generate_files()

        expected = {"/abc.html", "/123.php", "/test",
                    "/0/abc.html", "/0/123.php", "/0/test",
                    "/1/abc.html", "/1/123.php", "/1/test",
                    "/2/abc.html", "/2/123.php", "/2/test"}
        self.assertEqual(expected, {file["url"] for file in files})

    def test_generate_file_append_executable_suffixes_to_loaded_files_if_file_is_executable(self):
        database.valid_paths = load_paths(["/", "0"])
        database.files = load_files(["/abc", "123"], executable=True)
        conf.executables_suffixes = [".php", ".aspx"]

        files = self.generator.generate_files()

        expected = {"/abc.php", "/abc.aspx", "/123.php", "/123.aspx",
                    "/0/abc.php", "/0/abc.aspx", "/0/123.php", "/0/123.aspx"}
        self.assertEqual(expected, {file["url"] for file in files})

    def test_generate_file_append_file_suffixes_to_loaded_files_if_no_suffix_is_false(self):
        database.valid_paths = load_paths(["/", "0"])
        database.files = load_files(["/abc", "123"])
        conf.file_suffixes = [".txt", ".xml"]

        files = self.generator.generate_files()

        expected = {"/abc.txt", "/abc.xml", "/123.txt", "/123.xml",
                    "/0/abc.txt", "/0/abc.xml", "/0/123.txt", "/0/123.xml"}
        self.assertEqual(expected, {file["url"] for file in files})


def load_paths(path_list):
    loaded_paths = []
    for path in path_list:
        _path = {"url": path, "description": "desc", "timeout_count": 0, "severity": "warning"}
        loaded_paths.append(_path)
    return loaded_paths

def load_files(file_list, **kwargs):
    loaded_files = []
    for filename in file_list:
        file = {"url": filename, "description": "desc", "severity": "warning", "timeout_count": 0}
        file.update(**kwargs)
        loaded_files.append(file)
    return loaded_files
