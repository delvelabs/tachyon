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
from core import conf, database, utils
from core.workers import TestUrlExistsWorker
from core.threads import ThreadManager
from datetime import datetime, timedelta

def execute():
    manager = ThreadManager()
    utils.output_info(" - SpeedBenchmark Plugin: Starting speed benchmark on " + conf.target_host +
                      " with " + str(conf.thread_count) + " threads.")

    # Fetch the root once with each thread to get an averaged timing value
    start_time = datetime.now()

    #for thread_count in range(0, conf.thread_count):
    test_url = dict(conf.path_template)
    test_url['url'] = '/'
    test_url['description'] = 'SpeedBenchmark test point'
    database.fetch_queue.put(test_url)

    workers = manager.spawn_workers(1, TestUrlExistsWorker)
    manager.wait_for_idle(workers, database.fetch_queue)
    end_time = datetime.now()
    total_time = (end_time - start_time)

    # Compute the _approximate_ operation time
    estimated_time = total_time * len(database.valid_paths)

    utils.output_debug(" - SpeedBenchmark Plugin: " + str(total_time) + " elapsed.")
    utils.output_debug(" - SpeedBenchmark Plugin: " + str(estimated_time) + " estimated")

    # Pretty output
    minutes, remainder = divmod(estimated_time.seconds, 3600)
    seconds, millisecs = divmod(remainder, 60)

    utils.output_info(" - SpeedBenchmark Plugin: host scan is likely to take " +
                      str(minutes) + " minutes, " +
                      str(seconds) + " seconds.")
