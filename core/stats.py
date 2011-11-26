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

from core import database, textutils
from datetime import datetime
from threading import Lock

def update_stats(url):
    lock = Lock()
    lock.acquire()
    database.current_url = url
    lock.release()

def update_processed_items():
    lock = Lock()
    lock.acquire()
    database.item_count += 1
    lock.release()

def update_timeouts():
    lock = Lock()
    lock.acquire()
    database.timeouts += 1
    lock.release()

def output_stats():
    lock = Lock()
    lock.acquire()

    average_timeouts = database.timeouts / database.item_count
    estimated_future_timeouts = average_timeouts * database.fetch_queue.qsize()
    estimated_total_remaining = int(estimated_future_timeouts + database.fetch_queue.qsize())
    total_requests = database.item_count + database.timeouts
    elapsed_time = datetime.now() - database.scan_start_time
    request_per_seconds = elapsed_time / total_requests
    remaining = request_per_seconds * estimated_total_remaining

    textutils.output_info(str(total_requests / elapsed_time.seconds) + ' reqs/sec' + ', Done: ' + str(database.item_count) + ', Queued: ' + str(database.fetch_queue.qsize()) + ', Timeouts: ' +
        str(database.timeouts) + ', throttle: ' + str(database.throttle_delay) + "s, remaining: " + str(remaining)[:-7] + " (press ctrl+c again to exit)")

    lock.release()
