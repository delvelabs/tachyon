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

import Queue
from datetime import timedelta, datetime

""" Path list is used to hold loaded path from disk """
paths = list()

""" File list is used to hold loaded filenames from disk """
files = list()

""" Valid path is used to store the path that were found before merging with filenames """
valid_paths = list()

""" Fetch List contains all the url that have to be fetched by the workers """
fetch_queue = Queue.Queue()

""" messages output queue contains all the information,debug and timeout messages """
messages_output_queue = Queue.Queue()

""" results output contains the scan results """
results_output_queue = Queue.Queue()

""" Bad CRC database includes all computed crc that represents a false positive """
bad_crcs = list() 

""" namecache is used across the app to avoid adding duplicates url """
name_cache = dict()

""" Dns resolve cache """
dns_cache = dict()


# Stats values
item_count = 0
timeouts = 0
current_url = ''
