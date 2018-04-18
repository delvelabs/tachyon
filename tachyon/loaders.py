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
import json
import os.path as osp
import sys

from tachyon import textutils


def _get_data_dir():
    return osp.join(osp.dirname(sys.modules['tachyon'].__file__), 'data/')


def load_json_resource(name):
    data_path = osp.join(_get_data_dir(), name + '.json')
    return load_targets(data_path)


def load_targets(file):
    """ Load the list of target paths """
    loaded = []
    with open(file) as fp:
        try:
            data = json.load(fp)
            for section in data:
                loaded.extend(section["data"])
        except json.JSONDecodeError as e:
            textutils.output_error("Error when loading file %s: %s" % (file, str(e)))
    return loaded


def load_cookie_file(filename):
    try:
        with open(filename, 'r') as cookie_file:
            content = cookie_file.read()
            content = content.replace('Cookie: ', '')
            content = content.replace('\n', '')
            return content
    except IOError:
        textutils.output_info('Supplied cookie file not found, will use server provided cookies')
        return None
