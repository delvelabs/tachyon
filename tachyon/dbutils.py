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
#

from tachyon import database


def _get_cached_url_string(url_obj):
    if len(url_obj['url']) == 1 and url_obj['url'] == '/':
        return url_obj['url']

    return url_obj['url'].strip('/')


def add_path_to_fetch_queue(url_obj):
    """
     Add a path to the fetch queue but makes sure it's not already there.
     returns True if the path was not in the list, False if it's a duplicate
    """
    url_string = _get_cached_url_string(url_obj)
    if url_string not in database.path_cache:
        database.path_cache.add(url_string)
        return True
    else:
        return False


def add_file_to_fetch_queue(url_obj):
    """
     Add a file to the fetch queue but makes sure it's not already there.
     returns True if the file was not in the list, False if it's a duplicate
    """
    url_string = _get_cached_url_string(url_obj)
    if url_string not in database.file_cache:
        database.file_cache.add(url_string)
        return True
    else:
        return False
