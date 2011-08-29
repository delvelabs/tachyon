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
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more1336
# details.
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 59 Temple
# Place, Suite 330, Boston, MA  02111-1307  USA
#
from core import conf, database, utils
from core.fetcher import Fetcher
from datetime import datetime, timedelta

def execute():
    num_samples = 25
    
    utils.output_info(" - SpeedBenchmark Plugin: Executing " + str(num_samples) + " requests")

    # Fetch the root once with each thread to get an averaged timing value
    fetcher = Fetcher()
    target_url = conf.target_host + '/'

    
    max_time = timedelta(0) 
    for count in range(0, num_samples):
        start_time = datetime.now()
        response_code, content, headers = fetcher.fetch_url(target_url, conf.user_agent, timeout=conf.fetch_timeout_secs)
        end_time = datetime.now()
        total_time = end_time - start_time
        # max function
        if total_time > max_time:
            max_time = total_time
        

    utils.output_debug(" - SpeedBenchmark Plugin: " + str(max_time) + " max time.")
    
   
    # Get average time for fetch op
    fetch_operations = len(database.valid_paths) / conf.thread_count
    estimated_time = fetch_operations * max_time
    
    
    utils.output_debug(" - SpeedBenchmark Plugin: " + str(estimated_time) + " estimated")

    # Pretty output
    #minutes, remainder = divmod(estimated_time.total_seconds(), 3600)
    #seconds, millisecs = divmod(remainder, 60)

    utils.output_info(" - SpeedBenchmark Plugin: host scan is likely to take " + str(estimated_time))
                      #str(minutes) + " minutes, " +
                      #str(seconds) + " seconds.")
