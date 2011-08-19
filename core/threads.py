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
from core import utils

def wait_for_idle(workers, queue):
    """ Wait until fetch queue is empty and handle user interrupt """
    done = False
    
    while not done:
        try:
            if queue.empty():
                # Wait for all threads to return their stat
                queue.join()
                for worker in workers:
                    worker.kill_received = True
                
                # We are done!
                done = True
        except KeyboardInterrupt:
            utils.output_raw('')
            utils.output_info('Keyboard Interrupt Received, cleaning up threads')
            # Kill remaining workers
            for worker in workers:
                worker.kill_received = True
                if worker is not None and worker.isAlive():
                    worker.join(1)
                    
            # Kill the soft
            sys.exit()

def clean_workers(workers):
    for worker in workers:
        worker.kill_received = True
        if worker is not None and worker.isAlive():
            worker.join(1)
    
def spawn_workers(count, worker_type, display_output=True):
    """ Spawn a given number of workers and return a reference list to them """
    # Keep track of all worker threads
    workers = list()
    for thread_id in range(count):
        worker = worker_type(thread_id, display_output)
        worker.daemon = True
        workers.append(worker)
        worker.start()
    return workers
