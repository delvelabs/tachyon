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


import re
from core import database, conf, utils
from core.fetcher import Fetcher
from threading import Thread, Lock
from binascii import crc32
from Queue import Empty
from time import sleep

def update_stats(url):
    lock = Lock()
    lock.acquire()
    database.current_url = url
    lock.release()
    
def update_processed_items():
    lock = Lock()
    lock.acquire()
    database.item_count += 1
    lock.release()
    
def update_timeouts():
    lock = Lock()
    lock.acquire()
    database.timeouts += 1
    lock.release()
    

def handle_timeout(queued, url, thread_id, output=True):
    """ Handle timeout operation for workers """
    if not queued['timeout_count']:
        queued['timeout_count'] = 0

    if queued.get('timeout_count') < conf.max_timeout_count:
        new_timeout_count = queued.get('timeout_count') + 1
        queued['timeout_count'] = new_timeout_count
        utils.output_debug('Thread #' + str(thread_id) + ': re-queuing ' + str(queued))

        # Add back the timed-out item
        database.fetch_queue.put(queued)
    elif output:
        # We definitely timed out
        utils.output_timeout(queued.get('description') + ' at ' + url)
    
    # update timeout count   
    update_timeouts()
        

def compute_limited_crc(content, length):
    """ Compute the CRC of len bytes, use everything is len(content) is smaller than asked """
    if len(content) < length:
        return crc32(content[0:len(content) - 1]) 
    else:            
        return crc32(content[0:length - 1])


class Compute404CRCWorker(Thread):
    """
    This worker Generate a faked, statistically invalid filename to generate a 404 errror. The CRC32 checksum
    of this error page is then sticked to the path to use it to validate all subsequent request to files under
    that same path.
    """
    def __init__(self, thread_id, output=True):
        Thread.__init__(self)
        self.kill_received = False
        self.thread_id = thread_id
        self.fetcher = Fetcher()
        self.output = output

    def run(self):
        while not self.kill_received:
            try:
                # Non-Blocking get since we use the queue as a ringbuffer
                queued = database.fetch_queue.get(False)
                url = conf.target_host + queued.get('url')

                utils.output_debug("Computing specific 404 CRC for: " + str(url))
                update_stats(url)
                
                # Fetch the target url
                response_code, content, headers = self.fetcher.fetch_url(url, conf.user_agent, conf.fetch_timeout_secs)

                # Handle fetch timeouts by re-adding the url back to the global fetch queue
                # if timeout count is under max timeout count
                if response_code is 0 or response_code is 500:
                    handle_timeout(queued, url, self.thread_id, output=self.output)
                elif response_code in conf.expected_file_responses:
                    # Compute the CRC32 of this url. This is used mainly to validate a fetch against a model 404
                    # All subsequent files that will be joined to those path will use the path crc value since
                    # I think a given 404 will mostly be bound to a directory, and not to a specific file.
                    computed_checksum = compute_limited_crc(content, conf.crc_sample_len)

                    # Add new CRC to error crc checking
                    if computed_checksum not in database.bad_crcs:
                        database.bad_crcs.append(computed_checksum)

                    # Exception case for root 404, since it's used as a model for other directories
                    utils.output_debug("Computed and saved a 404 crc for: " + str(queued))
                    utils.output_debug("404 CRC'S: " + str(database.bad_crcs))

                    # The path is then added back to a validated list
                    #if queued not in database.valid_paths:
                       # database.valid_paths.append(queued) 

                # We are done
                update_processed_items()
                database.fetch_queue.task_done()

            except Empty:
                # Queue was empty but thread not killed, it means that more items could be added to the queue.
                # We sleep here to give a break to the scheduler/cpu. Since we are in a complete non-blocking mode
                # avoiding this raises the cpu usage to 100%
                sleep(0.1)
                continue

        utils.output_debug("Thread #" + str(self.thread_id) + " killed.")


class TestPathExistsWorker(Thread):
    """ This worker test if a path exists. Each path is matched against a fake generated path while scanning root. """
    def __init__(self, thread_id, output=True):
        Thread.__init__(self)
        self.kill_received = False
        self.thread_id = thread_id
        self.fetcher = Fetcher()
        self.output = output
        
    def run(self):
         while not self.kill_received:
            try:
                queued = database.fetch_queue.get(False)
                url = conf.target_host + queued.get('url')
                description = queued.get('description')
                utils.output_debug("Testing directory: " + url + " " + str(queued))
                update_stats(url)
                
                # Fetch directory
                response_code, content, headers = self.fetcher.fetch_url(url, conf.user_agent, conf.fetch_timeout_secs)
                
                # Fetch '/' but don't submit it to more logging/existance tests
                if queued.get('url') == '/':
                    if queued not in database.valid_paths:
                        database.valid_paths.append(queued)

                    database.fetch_queue.task_done()
                    continue


                # handle timeout
                if response_code in conf.timeout_codes:
                    handle_timeout(queued, url, self.thread_id, output=self.output)    
                elif response_code in conf.expected_path_responses:
                    crc = compute_limited_crc(content, conf.crc_sample_len)

                    utils.output_debug("Matching directory: " + str(queued) + " with crc: " + str(crc))
                    if response_code == 401:
                        # Output result, but don't keep the url since we can't poke in protected folder
                        utils.output_found('Password Protected - ' + description + ' at: ' + url)
                    elif crc not in database.bad_crcs:
                        # Add path to valid_path for future actions
                        database.valid_paths.append(queued)
                        
                        # Skip logging if directory listing is forbidden
                        # We still want to test subfiles.
                        if response_code != 403 and crc != 0:
                            utils.output_found(description + ' at: ' + url)
                        elif response_code == 403:
                            utils.output_found('Forbidden ' + description + ' at: ' + url)
                        


                # Mark item as processed
                update_processed_items()
                database.fetch_queue.task_done()
            except Empty:
                # We sleep here to give a break to the scheduler/cpu. Since we are in a complete non-blocking mode
                # avoiding this raises the cpu usage to 100%
                sleep(0.1)
                continue

        
    
class TestFileExistsWorker(Thread):
    """ This worker get an url from the work queue and call the url fetcher """
    def __init__(self, thread_id, output=True):
        Thread.__init__(self)
        self.kill_received = False
        self.thread_id = thread_id
        self.fetcher = Fetcher()
        self.output = output

    def run(self):
         while not self.kill_received:
            try:
                # Non-Blocking get since we use the queue as a ringbuffer
                queued = database.fetch_queue.get(False)
                url = conf.target_host + queued.get('url')
                description = queued.get('description')
                match_string = queued.get('match_string')

                utils.output_debug("Testing: " + url + " " + str(queued))
                update_stats(url)
                    
                # Fetch the target url
                if match_string:
                    response_code, content, headers = self.fetcher.fetch_url(url, conf.user_agent, conf.fetch_timeout_secs, limit_len=False)
                else:
                    response_code, content, headers = self.fetcher.fetch_url(url, conf.user_agent, conf.fetch_timeout_secs)

                # handle timeout
                if response_code in conf.timeout_codes:
                    handle_timeout(queued, url, self.thread_id, output=self.output)
                elif response_code in conf.expected_file_responses:
                    # At this point each directory should have had his 404 crc computed (tachyon main loop)
                    crc = compute_limited_crc(content, conf.crc_sample_len)
                    
                    utils.output_debug("Matching File: " + str(queued) + " with crc: " + str(crc))
                    
                    # If the CRC missmatch, and we have an expected code, we found a valid link
                    if crc not in database.bad_crcs:
                        # Content Test if match_string provided
                        if match_string and re.search(re.escape(match_string), content, re.I):
                            # Add path to valid_path for future actions
                            database.valid_paths.append(queued)
                            utils.output_found("String-Matched " + description + ' at: ' + url)
                        elif not match_string:
                            # Add path to valid_path for future actions
                            database.valid_paths.append(queued)
                            utils.output_found(description + ' at: ' + url)

                # Mark item as processed
                update_processed_items()
                database.fetch_queue.task_done()
            except Empty:
                # We sleep here to give a break to the scheduler/cpu. Since we are in a complete non-blocking mode
                # avoiding this raises the cpu usage to 100%
                sleep(0.1)
                continue



class PrintWorker(Thread):
    """ This worker is used to generate a synchronized non-overlapping console output. """

    def __init__(self):
        Thread.__init__(self)
        self.kill_received = False

    def run(self):
        while not self.kill_received:
            text = database.messages_output_queue.get()
            print text
            database.messages_output_queue.task_done()


class PrintResultsWorker(Thread):
    """ This worker is used to generate a synchronized non-overlapping console output for results """

    def __init__(self):
        Thread.__init__(self)
        self.kill_received = False

    def run(self):
        while not self.kill_received:
            text = database.results_output_queue.get()
            print text
            database.results_output_queue.task_done()

