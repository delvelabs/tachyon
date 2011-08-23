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
from core.fetcher import Fetcher
from datetime import datetime, timedelta

def execute():
    benchmark_runs = 10

    utils.output_info(" - SpeedBenchmark Plugin: Starting speed benchmark on " + conf.target_host +
                      " using " + str(benchmark_runs) + " fetches average.")

    # Fetch the root once with each thread to get an averaged timing value
    fetcher = Fetcher()
    
    total_time = timedelta(0)
    for count in range(0, benchmark_runs):
        start_time = datetime.now()
        response_code, content, headers = fetcher.fetch_url(conf.target_host, conf.user_agent, conf.fetch_timeout_secs)
        end_time = datetime.now()
        total_time += (end_time - start_time)
    

    # Compute the _approximate_ operation time
    estimated_time = (total_time / benchmark_runs) * len(database.valid_paths)

    utils.output_debug(" - SpeedBenchmark Plugin: " + str(total_time) + " elapsed.")
    utils.output_debug(" - SpeedBenchmark Plugin: " + str(estimated_time) + " estimated")

    # Pretty output
    minutes, remainder = divmod(estimated_time.seconds, 3600)
    seconds, millisecs = divmod(remainder, 60)

    utils.output_info(" - SpeedBenchmark Plugin: host scan is likely to take " +
                      str(minutes) + " minutes, " +
                      str(seconds) + " seconds.")
