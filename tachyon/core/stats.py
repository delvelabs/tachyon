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

from . import database, textutils
from datetime import datetime, timedelta

def update_stats(url):
    database.current_url = url

def update_processed_items():
    database.successful_fetch_count += 1

def output_stats(workers=None):
    elapsed_time = datetime.now() - database.scan_start_time
    if not elapsed_time.seconds:
        request_per_seconds = 0
    else:
        request_per_seconds = database.successful_fetch_count / elapsed_time.seconds

    if request_per_seconds:
        remaining_seconds = int(database.fetch_queue.qsize() / request_per_seconds)
        remaining_timedelta = timedelta(seconds=remaining_seconds)
    else:
        remaining_seconds = 0
        remaining_timedelta = timedelta(seconds=remaining_seconds)

    request_per_seconds = "%.2f" % round(request_per_seconds,2)

    stats_string = ''.join([
        str(request_per_seconds), ' reqs/sec',
        ', Done: ', str(database.successful_fetch_count),
        ', Queued: ', str(database.fetch_queue.qsize()),
        ', Timeouts: ', str(database.total_timeouts), ' (~', str(database.latest_successful_request_time), 's)',
        ', Remaining: ', str(remaining_timedelta),
        ', Workers: ', str(len(workers)),
        ' (hit ctrl+c again to exit)'
    ])

    textutils.output_info(stats_string)


