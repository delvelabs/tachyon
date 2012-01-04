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
import urllib3
from urllib3.exceptions import MaxRetryError
from core import conf

def get_config_val():
    ip, port, run_id = conf.subatomic.split(':')
    url = 'http://' + ip + ':' + port
    return url, run_id

def post_message(message):
    try:
        url, run_id = get_config_val()
        pool = urllib3.connection_from_url(url)
        fields = {'run_id': run_id, 'data' : message}
        pool.post_url('/process_manager/notify', fields)
    except MaxRetryError:
        print("Message delivery error: " + message)
