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


import tachyon.core.database as database
import tachyon.core.conf as conf


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

    def generate_files(self):
        files = list()
        for path in database.valid_paths:
            # Combine current path with all files and suffixes if enabled
            for filename in database.files:
                if filename.get('no_suffix'):
                    url = self._join_path(path["url"], filename["url"])
                    new_filename = self._create_file(filename.copy(), url=url, is_file=True, no_suffix=True)
                    files.append(new_filename)
                elif filename.get('executable'):
                    for executable_suffix in conf.executables_suffixes:
                        url = self._join_path(path["url"], filename["url"] + executable_suffix)
                        new_filename = self._create_file(filename.copy(), url=url, is_file=True, executable=True)
                        files.append(new_filename)
                else:
                    for suffix in conf.file_suffixes:
                        url = self._join_path(path["url"], filename["url"] + suffix)
                        new_filename = self._create_file(filename.copy(), url=url, is_file=True)
                        files.append(new_filename)
        return files

    def _create_file(self, base_file, **kwargs):
        base_file.update(**kwargs)
        return base_file

    def _join_path(self, base_path, file_path):
        if base_path == "/":
            return"/{file}".format(file=file_path.strip("/"))
        else:
            return "/{path}/{file}".format(path=base_path.strip("/"), file=file_path.strip("/"))
