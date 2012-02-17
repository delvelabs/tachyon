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

from core import database

def _get_stripped_url(url):
    if len(url) == 1 and url == '/':
        return url
    elif len(url) > 1 and  url.endswith('/'):
        return url[:-1].strip('/')
    else:
        return url.strip('/')


def _add_url_to_cache(url):
    """
    Add a stripped url to the name cache without inflicting on leading /
    which denotes a directory and matters in a lot of webserver implementation
    """
    stripped_url = _get_stripped_url(url)
    database.name_cache.add(stripped_url)

def _is_url_in_cache(url):
    """ Test if an url has already been tested """
    stripped_url = _get_stripped_url(url)
    return stripped_url in database.name_cache

def add_url_fetch_queue(url):
    """
     Add an url to the fetch queue but makes sure it's not already there.
     returns True if the url was not in the list, False if it's a duplicate
    """
    if not _is_url_in_cache(url['url']):
        database.fetch_queue.put(url)
        _add_url_to_cache(url['url'])
        return True
    else:
        return False