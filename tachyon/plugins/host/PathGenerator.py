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

from datetime import date

from tachyon import conf, textutils, database


plugin_settings = conf.plugin_settings["PathGenerator"]


def add_generated_path(path):
    current_template = conf.path_template.copy()
    current_template['description'] = 'Computer generated path'
    current_template['is_file'] = False
    current_template['url'] = '/' + path
    current_template['handle_redirect'] = "ignoreRedirect" not in plugin_settings
    database.paths.append(current_template)


def add_generated_file(file):
    """ Add file to database """
    current_template = conf.path_template.copy()
    current_template['description'] = 'Computer generated file'
    current_template['url'] = file
    current_template['handle_redirect'] = "ignoreRedirect" not in plugin_settings
    database.files.append(current_template)


async def execute(hammertime):
    """ Generate common simple paths (a-z, 0-9) """
    path_added = 0
    file_added = 0

    if "skipAlpha" not in plugin_settings:
        for char in range(ord('a'), ord('z')+1):
            add_generated_path(chr(char))
            path_added += 1
            add_generated_file(chr(char))
            file_added += 1

    if "skipNumeric" not in plugin_settings:
        for char in range(ord('0'), ord('9')+1):
            add_generated_path(chr(char))
            path_added += 1
            add_generated_file(chr(char))
            file_added += 1

    if "skipYear" not in plugin_settings:
        for year in range(1990, date.today().year + 5):
            add_generated_path(str(year))
            path_added += 1

    textutils.output_info(' - PathGenerator Plugin: added ' + str(path_added) + ' computer generated path.')
    textutils.output_info(' - PathGenerator Plugin: added ' + str(file_added) + ' computer generated files.')
