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

from time import sleep
from . import database, textutils, stats


class ThreadManager(object):

    def wait_for_idle(self, workers, queue):
            """ Wait until fetch queue is empty and handle user interrupt """
            while not database.kill_received and not queue.empty():
                try:
                    # Make sure everything is done before sending control back to application
                    textutils.output_debug("Threads: joining queue of size: " + str(queue.qsize()))
                    queue.join()
                    textutils.output_debug("Threads: join done")
                except KeyboardInterrupt:
                    try:
                        stats.output_stats(workers)
                        sleep(1)  # The time you have to re-press ctrl+c to kill the app.
                    except KeyboardInterrupt:
                        textutils.output_info('Keyboard Interrupt Received, waiting for blocking threads to exit')
                        # Clean reference to sockets
                        database.connection_pool = None
                        database.kill_received = True
                        self.kill_workers(workers)
                        sys.exit(0)

            # Make sure we get all the worker's results before continuing the next step
            self.kill_workers(workers)

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

    def kill_workers(self, workers):
        for worker in workers:
            if worker and worker.isAlive():
                worker.kill_received = True
                worker.join(1)
