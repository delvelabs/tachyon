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
from core import utils, database
from time import sleep

class ThreadManager(object):
    def __init__(self):
        self.kill_received = False 
     
        
    def wait_for_idle(self, workers, queue):
            """ Wait until fetch queue is empty and handle user interrupt """
            while not self.kill_received and not queue.empty():
                try:
                    sleep(0.1)
                except KeyboardInterrupt:
                    utils.output_message_raw('')
                    utils.output_info('Keyboard Interrupt Received, cleaning up threads')
                    self.kill_received = True
                    
                    # Kill remaining workers but don't join the queue (we want to abort:))
                    for worker in workers:
                        worker.kill_received = True
                        if worker is not None and worker.isAlive():
                            worker.join(1)
        
                    # Kill the soft
                    sys.exit()
           
           
            # Make sure everything is done before sending control back to application
            utils.output_debug("Threads: joining queue of size: " + str(queue.qsize()))
            queue.join()
            utils.output_debug("Threads: join done")

            for worker in workers:
                worker.kill_received = True
                worker.join()
    
    
    def spawn_workers(self, count, worker_type):
        """ Spawn a given number of workers and return a reference list to them """
        # Keep track of all worker threads
        workers = list()
        for thread_id in range(count):
            worker = worker_type(thread_id)
            worker.daemon = True
            workers.append(worker)
            worker.start()
        return workers
        