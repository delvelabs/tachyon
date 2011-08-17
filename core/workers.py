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

import uuid
from core import database, conf, utils
from core.fetcher import Fetcher
from urlparse import urljoin
from threading import Thread
from binascii import crc32

def handle_queue_timeout(queued, url, thread_id):
    """ Handle queue timeout operation for workers"""
    if not queued['timeout_count']:
        queued['timeout_count'] = 0

    if queued.get('timeout_count') < conf.max_timeout_count:
        new_timeout_count = queued.get('timeout_count') + 1
        queued['timeout_count'] = new_timeout_count

        if conf.debug:
            utils.output_info('Thread #' + str(thread_id) + ': re-queuing ' + str(queued))

        # Add back the timed-out item
        database.fetch_queue.put(queued)
    else:
        # We definitely timed out
        utils.output_timeout(url)


class Compute404CRCWorker(Thread):
    """
    This worker Generate a faked, statistically invalid filename to generate a 404 errror. The CRC32 checksum
    of this error page is then sticked to the path to use it to validate all subsequent request to files under
    that same path.
    """
    def __init__(self, thread_id):
        Thread.__init__(self)
        self.kill_received = False
        self.thread_id = thread_id
        self.fetcher = Fetcher()

    def run(self):
        while not self.kill_received:
            # don't wait for any items if empty
            if not database.fetch_queue.empty():
                queued = database.fetch_queue.get()
                random_file = str(uuid.uuid4())
                url = urljoin(conf.target_host, queued.get('url') + '/' + random_file)

                # Fetch the target url
                response_code, content, headers = self.fetcher.fetch_url(url, conf.user_agent, conf.fetch_timeout_secs)

                # Handle fetch timeouts by re-adding the url back to the global fetch queue
                # if timeout count is under max timeout count
                if response_code is 0:
                    handle_queue_timeout(queued, url, self.thread_id)

                # Compute the CRC32 of this url. This is used mainly to validate a fetch against a model 404
                # All subsequent files that will be joined to those path will use the path crc value since
                # I think a given 404 will mostly be bound to a directory, and not to a specific file.
                # This step is only made in initial discovery mode. (Should be moved to a separate worker)
                queued['computed_404_crc'] = crc32(content)

                # The path is then added back to a validated list
                database.valid_paths.append(queued)

                if conf.debug:
                    utils.output_debug("Computed Checksum for: " + str(queued))

                # We are done
                database.fetch_queue.task_done()




class FetchUrlWorker(Thread):
    """ This worker get an url from the work queue and call the url fetcher """
    def __init__(self, thread_id, discovery):
        Thread.__init__(self)
        self.kill_received = False
        self.thread_id = thread_id
        self.fetcher = Fetcher()

    def run(self):
        while not self.kill_received:
            # don't wait for any items if empty
            if not database.fetch_queue.empty():
                queued = database.fetch_queue.get()
                url = urljoin(conf.target_host, queued.get('url'))
                expected_responses = queued.get('expected_response')
                description = queued.get('description')
                match_string = queued.get('match_string')
                computed_404_crc = queued.get('computed_404_crc')

                # Check if a timeout value is present
                if not queued['timeout_count']:
                    queued['timeout_count'] = 0

                # Fetch the target url
                response_code, content, headers = self.fetcher.fetch_url(url, conf.user_agent, conf.fetch_timeout_secs)

                if response_code is 0:
                    handle_queue_timeout(queued, url, self.thread_id)


                # Response is good, test if the crc match a 404
                if response_code in expected_responses:
                    if computed_404_crc:
                        actual_crc = crc32(content)

                        # if the CRC differ, we have a legitimate hit.
                        if actual_crc != computed_404_crc:

                            pass



                    # Fuse with current url. (/test become url.dom/test)
                    queued['url'] = urljoin(conf.target_host, queued['url'])

                    # If we don't blacklist, just show the result
                    if not conf.content_type_blacklist:
                        if self.discovery:
                            if response_code == 401:
                                utils.output_found('*Password Protected* ' + description + ' at: ' + url)
                            else:
                                utils.output_found(description + ' at: ' + url)

                        # Add to valid path
                        database.valid_paths.append(queued)

                    # if we DO blacklist but content is not blacklisted, show the result
                    elif content_type not in content_type_blacklist:
                        if self.discovery:
                            if response_code == 401:
                                utils.output_found('*Password Protected* ' + description + ' at: ' + url)
                            else:
                                utils.output_found(description + ' at: ' + url)

                        # Add to valid path
                        database.valid_paths.append(queued)

                # Mark item as processed
                database.fetch_queue.task_done()


class PrintWorker(Thread):
    """ This worker is used to generate a synchronized non-overlapping console output. """

    def __init__(self):
        Thread.__init__(self)
        self.kill_received = False

    def run(self):
        while not self.kill_received:
            text = database.output_queue.get()
            print text
            database.output_queue.task_done()

