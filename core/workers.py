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
        self.thread_id = thread_id
        self.fetcher = Fetcher()

    def run(self):
        while True:
            queued = database.fetch_queue.get()
            url = urljoin(conf.target_host, queued.get('url'))
            expected = queued.get('expected_response')
            response_code, content, headers = self.fetcher.fetch_url(url, 'HEAD', conf.user_agent, False, conf.fetch_timeout_secs)

            if response_code is 0: # timeout
                utils.output('[TIMEOUT] Thread #' + str(self.thread_id) + ': ' + url)
            elif response_code in expected:
                if conf.debug:
                    utils.output('Thread #' + str(self.thread_id) + ': ' + url)
                else:
                    utils.output(url)
            else:
                if conf.debug:
                    utils.output('[ERROR] Thread #' + str(self.thread_id) + ': ' + url)
                else:
                    utils.output(url)


            # Mark item as processed
            database.fetch_queue.task_done()


class PrintWorker(Thread):
    """ This worker is used to generate a synchronized non-overlapping console output. """
    def run(self):
        while True:
            text = database.output_queue.get()
            print text
            database.output_queue.task_done()
