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


from .output import PrettyOutput, JSONOutput


output_manager = None


def output_error(text):
    output_manager.output_error(text)


def output_info(text):
    output_manager.output_info(text)


def output_timeout(text):
    output_manager.output_timeout(text)


def output_found(text, data=None):
    output_manager.output_result(text, data)


def flush():
    output_manager.flush()


def init_log(json_output):
    global output_manager
    if json_output:
        output_manager = JSONOutput()
    else:
        output_manager = PrettyOutput()

    return output_manager
