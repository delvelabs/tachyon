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


import tachyon.database as database


class PathGenerator:

    def generate_paths(self, *, use_valid_paths):
        generated_paths = []
        if use_valid_paths:
            generated_paths.extend(self._create_new_paths_from_valid_paths())
            database.path_cache.update(path["url"] for path in generated_paths)
        else:
            generated_paths.extend([path for path in self._database_paths()])
            generated_paths.extend([file for file in self._use_files_as_paths()])
        return generated_paths

    def _database_paths(self):
        for path in database.paths:
            if path["url"] not in database.path_cache:
                database.path_cache.add(path["url"])
                yield path

    def _use_files_as_paths(self):
        for file in database.files:
            path = "/%s" % file["url"]
            if not file.get("no_suffix") and path not in database.path_cache:
                file_as_path = file.copy()
                file_as_path["url"] = path
                database.path_cache.add(path)
                yield file_as_path

    def _create_new_paths_from_valid_paths(self):
        new_paths = []
        for path in database.valid_paths:
            for _path in database.paths:
                new_path = self._join_paths(path, _path)
                if new_path is not None and new_path["url"] not in database.path_cache:
                    new_paths.append(new_path)
        return new_paths

    def _join_paths(self, leading_path, trailing_path):
        if leading_path["url"] != "/" and trailing_path["url"] != "/":
            new_path = trailing_path.copy()
            new_path["url"] = leading_path["url"] + trailing_path["url"]
            return new_path
        return None


class FileGenerator:

    def __init__(self):
        self.file_suffixes = ['', '.sql', '.bak', '-bak', '.old', '-old', '.dmp', '.dump', '.zip', '.rar', '.7z',
                              '.tar.gz', '.tar.bz2', '.tar', '.tgz', '~', '.conf.old', '.conf', '.config', '.conf.orig',
                              '.conf.bak', '.cnf', '.cfg', '.ini', '.inc', '.inc.old', '.inc.orig', '.log', '.txt',
                              '_log', '.passwd', '.php.bak', '.php.old', '.php.inc', '.php.orig', '.sql.old',
                              '.sql.bak', '0', '1', '2', '.xml', '.csv', '.wsdl', '.pwd', '.yml']
        self.executables_suffixes = ['.php', '.asp', '.aspx', '.pl', '.cgi', '.cfm']

    def generate_files(self, skip_root=False):
        files = list()
        for path in database.valid_paths:
            if not skip_root or not self._is_root(path):
                files.extend(self._add_all_possible_files_to_path(path))
        return files

    def _is_root(self, path):
        if path == "/":
            return True
        elif isinstance(path, dict):
            return self._is_root(path["url"])
        else:
            return False

    def _add_all_possible_files_to_path(self, path):
        for file in database.files:
            if file.get('no_suffix'):
                new_filename = self._create_file(file, path, is_file=True, no_suffix=True)
                yield new_filename
            elif file.get('executable'):
                yield from self._create_executable_files(path, file)
            else:
                yield from self._create_files_with_suffixe(path, file)

    def _create_executable_files(self, path, file):
        for executable_suffix in self.executables_suffixes:
            new_filename = self._create_file(file, path, suffix=executable_suffix, is_file=True, executable=True)
            yield new_filename

    def _create_files_with_suffixe(self, path, file):
        for suffix in self.file_suffixes:
            new_filename = self._create_file(file, path, suffix=suffix, is_file=True)
            yield new_filename

    def _create_file(self, base_file, path, suffix="", **kwargs):
        url = self._join_path(path["url"], base_file["url"] + suffix)
        file = base_file.copy()
        file.update(url=url, **kwargs)
        return file

    def _join_path(self, base_path, file_path):
        if base_path == "/":
            return"/{file}".format(file=file_path.strip("/"))
        else:
            return "/{path}/{file}".format(path=base_path.strip("/"), file=file_path.strip("/"))
