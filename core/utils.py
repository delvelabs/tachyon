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

from core import database, conf
from datetime import datetime


def output_raw(text):
    """ Output text to the synchronized output queue """
    database.output_queue.put(text)
      
def output(text):
    """ Output text to the synchronized output queue """
    output_raw('[' + str(datetime.now().strftime("%H:%M:%S")) + '] ' + text)

def output_error(text):
    """ Output text to the synchronized output queue """
    output('[ERROR] ' + text)
    
def output_info(text):
    """ Output text to the synchronized output queue """
    output('[INFO] ' + text)
    
def output_timeout(text):
    """ Output text to the synchronized output queue """
    output('[TIMEOUT] ' + text)
    
def output_found(text):
    """ Output text to the synchronized output queue """
    output('[FOUND] ' + text)
    
def output_debug(text):
    """ Output text to the synchronized output queue """
    output('[DEBUG] ' + text)
        

def sanitize_config():
    """ Sanitize configuration values """
    if not conf.target_host.startswith('http://'):
        conf.target_host = 'http://' + conf.target_host

    if not conf.target_host.endswith('/'):
        conf.target_host += '/'