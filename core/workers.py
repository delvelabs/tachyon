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

from core import database, conf, utils
from core.fetcher import Fetcher
from urlparse import urljoin
from threading import Thread

class FetchUrlWorker(Thread):
    """ This worker get an url from the work queue and call the url fetcher """
    def __init__(self, thread_id):
        Thread.__init__(self)
        self.kill_received = False
        self.thread_id = thread_id
        self.fetcher = Fetcher()
       

    def run(self):
        while not self.kill_received:
            queued = database.fetch_queue.get()
            url = urljoin(conf.target_host, queued.get('url'))
            expected = queued.get('expected_response')
            description = queued.get('description')
            
            if conf.use_get:
                method = 'GET'
            else:
                method = 'HEAD'
                
            response_code, content, headers = self.fetcher.fetch_url(url, method, conf.user_agent, False, conf.fetch_timeout_secs)
            
            if conf.debug:
                utils.output_info("Thread #" + str(self.thread_id) + ": " + str(queued))
                
            if response_code is 0: # timeout
                if queued.get('timeout_count') < conf.max_timeout_count:
                    new_timeout_count = queued.get('timeout_count') + 1
                    queued['timeout_count'] = new_timeout_count
                    
                    if conf.debug:
                        utils.output_info('Thread #' + str(self.thread_id) + ': re-queuing ' + str(queued))
                        
                    # Add back the timed-out item
                    database.fetch_queue.put(queued)
                else:
                    utils.output_timeout(url)
                    
            elif response_code in expected:
                if response_code == 401:
                    utils.output_found('*Password Protected* ' + description + ' at: ' + url)
                else:
                    utils.output_found(description + ' at: ' + url)
                    

            # Mark item as processed
            database.fetch_queue.task_done()


class PrintWorker(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.kill_received = False
     
    """ This worker is used to generate a synchronized non-overlapping console output. """
    def run(self):
        while not self.kill_received:
            text = database.output_queue.get()
            print text
            database.output_queue.task_done()

