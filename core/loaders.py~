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
#

import ast
import codecs
from core import database
from exceptions import SyntaxError

def load_file_list(file):
    """ Load the list of target files and combines them with paths"""
    file_list = codecs.open(file, 'r', 'UTF-8')
    tmp_list = list()

    for file in file_list:
        file = file.strip()
        if len(file) > 0 and '#' not in file:
            parsed_path = ast.literal_eval(file)
            
            # Add processing values
            parsed_path['timeout_count'] = 0
            
            # Add on root
            tmp_list.append(parsed_path)

            # Combine with preload list
            for item in database.preload_list:
                try:
                    # copy before adding
                    file_path = dict(parsed_path)
                    file_path['url'] = item.get('url') + file_path.get('url')
                    tmp_list.append(file_path)
                except SyntaxError as (errno, strerror):
                    print 'File parsing error: ', strerror

    for loaded in tmp_list:
        database.preload_list.append(loaded)

    file_list.close()


def load_path_file(file):
    """ Load the list of target paths """
    path_list = codecs.open(file, 'r', 'UTF-8')

    for path in path_list:
        path = path.strip()
        if len(path) > 0 and '#' not in path:
            try:
                # Add processing values
                parsed_path = ast.literal_eval(path)
                parsed_path['timeout_count'] = 0
                database.preload_list.append(parsed_path)
            except SyntaxError as (errno, strerror):
                print 'Path parsing error: ', strerror

    path_list.close()

