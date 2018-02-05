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


class PathGenerator:

    def generate_paths(self, *, use_valid_paths):
        generated_paths = []
        if use_valid_paths:
            generated_paths.extend(self._create_new_paths_from_valid_paths())
        else:
            generated_paths.extend(database.paths)
            generated_paths.extend(self._use_files_as_paths())
        database.path_cache.update(path["url"] for path in generated_paths)
        return generated_paths

    def _use_files_as_paths(self):
        files_as_paths = []
        for file in database.files:
            if not file.get("no_suffix"):
                files_as_paths.append(file)
        return files_as_paths

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
