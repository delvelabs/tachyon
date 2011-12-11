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

import re
from core import database, conf
from datetime import datetime


def output_result_raw(text):
    """ Output raw result text to the synchronized result output queue """
    database.results_output_queue.put(text)


def output_result(text):
    """ Output result text to the synchronized result output queue """
    output_result_raw('[' + str(datetime.now().strftime("%H:%M:%S")) + '] ' + text)


def output_message_raw(text):
    """ Output raw text to the synchronized output queue """
    database.messages_output_queue.put(text)


def output_message(text):
    """ Output text to the synchronized output queue """
    output_message_raw('[' + str(datetime.now().strftime("%H:%M:%S")) + '] ' + text)


def output_error(text):
    """ Output text to the synchronized output queue """
    if not conf.raw_output:
        output_result('[ERROR] ' + text)


def output_info(text):
    """ Output text to the synchronized output queue """
    if not conf.raw_output:
        output_message('[INFO] ' + text)


def output_timeout(text):
    """ Output text to the synchronized output queue """
    if not conf.raw_output:
        output_result('[TIMEOUT] ' + text)


def output_found(text):
    """ Output text to the synchronized output queue """
    if conf.raw_output:
        output_result_raw(text)
    else:
        output_result('[FOUND] ' + text)


def output_debug(text):
    """ Output text to the synchronized output queue """
    if conf.debug:
        output_message('[DEBUG] ' + text)
        