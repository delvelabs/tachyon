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

try:
    import queue as Queue
except ImportError:
    import Queue

from core import conf
from datetime import datetime

""" Connection pool, to be adjusted by tachyon after initial host benchmark """
connection_pool = None

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

""" Crafted 404's database """
crafted_404s = list()

""" caches are used across the app to avoid adding duplicates urls """
path_cache = set()
file_cache = set()

""" Dns resolve cache """
dns_cache = dict()

""" Scan start time """
scan_start_time = datetime.now()

"""Timeout management """
latest_successful_request_time = conf.fetch_timeout_secs
total_request_time = 0
total_timeouts = 0

""" App global kill """
kill_received = False


""" Session cookie """
session_cookie = None

""" Stats values """
successful_fetch_count = 0

""" Last printed len """
last_printed_len = 0
