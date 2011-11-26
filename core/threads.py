#!/usr/bin/python
#
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

import sys
from core import textutils, database
from time import sleep
from threading import Lock
from datetime import datetime

class ThreadManager(object):
    def __init__(self):
        self.kill_received = False 
     
        
    def wait_for_idle(self, workers, queue):
            """ Wait until fetch queue is empty and handle user interrupt """
            while not self.kill_received and not queue.empty():
                try:
                    sleep(0.1)
                except KeyboardInterrupt:
                    # output stats
                    try:
                        lock = Lock()
                        lock.acquire()

                        # move this somewhere else
                        textutils.output_message_raw('')
                        average_timeouts = database.timeouts / database.item_count
                        estimated_future_timeouts = average_timeouts * database.fetch_queue.qsize()
                        estimated_total_remaining = int(estimated_future_timeouts + database.fetch_queue.qsize())
                        total_requests = database.item_count + database.timeouts
                        elapsed_time = datetime.now() - database.scan_start_time
                        request_per_seconds = elapsed_time / total_requests
                        remaining = request_per_seconds * estimated_total_remaining  

                        textutils.output_info('Done: ' + str(database.item_count) + ', remaining: ' + str(database.fetch_queue.qsize()) + ', timeouts: ' +
                            str(database.timeouts) + ', throttle: ' + str(database.throttle_delay) + "s, remaining: " + str(remaining)[:-7] + " (press ctrl+c again to exit)")
                        # end of things to move

                        lock.release()
                        sleep(1)  
                    except KeyboardInterrupt:
                        textutils.output_info('Keyboard Interrupt Received, cleaning up threads')
                        self.kill_received = True
                        
                        # Kill remaining workers but don't join the queue (we want to abort:))
                        for worker in workers:
                            worker.kill_received = True
                            if worker is not None and worker.isAlive():
                                worker.join(1)
            
                        # Kill the soft
                        sys.exit()  
           
           
            # Make sure everything is done before sending control back to application
            textutils.output_debug("Threads: joining queue of size: " + str(queue.qsize()))
            queue.join()
            textutils.output_debug("Threads: join done")

            for worker in workers:
                worker.kill_received = True
                worker.join()
    
    
    def spawn_workers(self, count, worker_type, output=True):
        """ Spawn a given number of workers and return a reference list to them """
        # Keep track of all worker threads
        workers = list()
        for thread_id in range(count):
            worker = worker_type(thread_id, output=True)
            worker.daemon = True
            workers.append(worker)
            worker.start()
        return workers
        