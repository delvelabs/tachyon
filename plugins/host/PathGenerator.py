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

from core import conf, database, textutils

def add_generated_path(char):
    """ Add path to database """
    current_template = dict(conf.path_template)
    current_template['description'] = 'Computer generated path'
    current_template['url'] = '/' + chr(char)
    if current_template not in database.paths:
        textutils.output_debug(' - PathGenerator Plugin Generated: ' + str(current_template))
        database.paths.append(current_template)
        
def add_generated_file(char):
    """ Add path to database """
    current_template = dict(conf.path_template)
    current_template['description'] = 'Computer generated path'
    current_template['url'] = chr(char)
    if current_template not in database.files:
        textutils.output_debug(' - PathGenerator Plugin Generated: ' + str(current_template))
        database.files.append(current_template)


def execute():
    """ Generate common simple paths (a-z, 0-9) """
    path_added = 0
    file_added = 0
    for char in range(ord('a'), ord('z')):
        add_generated_path(char)
        path_added += 1
        add_generated_file(char)
        file_added += 1    

    for char in range(ord('0'), ord('9')):
        add_generated_path(char)
        path_added += 1
        add_generated_file(char)
        file_added += 1    


    textutils.output_info(' - PathGenerator Plugin: added ' + str(path_added) + ' computer generated path.')
    textutils.output_info(' - PathGenerator Plugin: added ' + str(file_added) + ' computer generated files.')
