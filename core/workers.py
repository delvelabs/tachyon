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
import sys
from core import database, conf, stats, textutils, throttle
from core.fetcher import Fetcher
from difflib import SequenceMatcher
from Queue import Empty
from threading import Thread

def handle_timeout(queued, url, thread_id, output=True):
    """ Handle timeout operation for workers """
    if not queued['timeout_count']:
        queued['timeout_count'] = 0

    if queued.get('timeout_count') < conf.max_timeout_count:
        new_timeout_count = queued.get('timeout_count') + 1
        queued['timeout_count'] = new_timeout_count
        textutils.output_debug('Thread #' + str(thread_id) + ': re-queuing ' + str(queued))

        # Add back the timed-out item
        database.fetch_queue.put(queued)
    elif output:
        # We definitely timed out
        textutils.output_timeout(queued.get('description') + ' at ' + url)

    # update timeout count
    stats.update_timeouts()

def test_valid_result(content):
    # Tweak the content len
    if len(content) > conf.file_sample_len:
        content = content[0:conf.file_sample_len -1]

    is_valid_result = True

    for fingerprint in database.crafted_404s:
        matcher = SequenceMatcher(isjunk=None, a=fingerprint, b=content, autojunk=False)

        # This content is almost similar to a generated 404, therefore it's a 404.
        if matcher.ratio() > 0.8:
            is_valid_result = False
            break

    return is_valid_result

class FetchCrafted404Worker(Thread):
    """
    This worker fetch lenght-limited 404 footprint and store them for Ratcliff-Obershelf comparing
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
                url = conf.target_base_path + queued.get('url')

                textutils.output_debug("Fetching crafted 404: " + str(url))
                stats.update_stats(url)

                # Fetch the target url
                timeout = False
                response_code, content, headers = self.fetcher.fetch_url(url, conf.user_agent, conf.fetch_timeout_secs)

                # Handle fetch timeouts by re-adding the url back to the global fetch queue
                # if timeout count is under max timeout count
                if response_code is 0 or response_code is 500:
                    handle_timeout(queued, url, self.thread_id, output=self.output)
                    # increase throttle delay
                    throttle.increase_throttle_delay()
                    timeout = True
                elif response_code in conf.expected_file_responses:
                    # The server responded with whatever code but 404 or invalid stuff (500). We take a sample
                    if len(content) < conf.file_sample_len:
                        crafted_404 = content[0:len(content) - 1]
                    else:
                        crafted_404 = content[0:conf.file_sample_len - 1]

                    database.crafted_404s.append(crafted_404)
                    

                    # Exception case for root 404, since it's used as a model for other directories
                    textutils.output_debug("Computed and saved a sample 404 for: " + str(queued) + ": " + crafted_404)

                # Decrease throttle delay if needed
                if not timeout:
                    throttle.decrease_throttle_delay()

                # Dequeue item
                stats.update_processed_items()
                database.fetch_queue.task_done()

            except Empty:
                continue

        textutils.output_debug("Thread #" + str(self.thread_id) + " killed.")


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
                url = conf.target_base_path + queued.get('url')
                description = queued.get('description')
                textutils.output_debug("Testing directory: " + url + " " + str(queued))

                stats.update_stats(url)

                # Throttle if needed
               # if throttle.get_throttle() > 0:
                  #  sleep(throttle.get_throttle())

                # Add trailing / for paths
                if url[:-1] != '/' and url != '/':
                    url += '/'

                # Fetch directory
                timeout = False
                response_code, content, headers = self.fetcher.fetch_url(url, conf.user_agent, conf.fetch_timeout_secs, limit_len=False)

                # Fetch '/' but don't submit it to more logging/existance tests
                if queued.get('url') == '/':
                    if queued not in database.valid_paths:
                        database.valid_paths.append(queued)

                    database.fetch_queue.task_done()
                    continue

                if response_code == 500:
                    textutils.output_debug("HIT 500 on: " + str(queued))

                # handle timeout
                if response_code in conf.timeout_codes:
                    handle_timeout(queued, url, self.thread_id, output=self.output)
                    # increase throttle delay
                    throttle.increase_throttle_delay()
                    timeout = True
                elif response_code in conf.expected_path_responses:
                    # Compare content with generated 404 samples
                    is_valid_result = test_valid_result(content)

                    # Skip subfile testing if forbidden
                    if response_code == 401:
                        # Output result, but don't keep the url since we can't poke in protected folder
                        textutils.output_found('Password Protected - ' + description + ' at: ' + conf.target_host + url)
                    elif is_valid_result:
                        # Add path to valid_path for future actions
                        database.valid_paths.append(queued)

                        if response_code == 500:
                            textutils.output_found('ISE, ' + description + ' at: ' + conf.target_host + url)    
                        elif response_code == 403:
                            textutils.output_found('*Forbidden* ' + description + ' at: ' + conf.target_host + url)
                        else:
                            textutils.output_found(description + ' at: ' + conf.target_host + url)


                # Decrease throttle delay if needed
                if not timeout:	
                    throttle.decrease_throttle_delay()
					
                # Mark item as processed
                stats.update_processed_items()
                database.fetch_queue.task_done()
            except Empty:
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
                url = conf.target_base_path + queued.get('url')
                description = queued.get('description')
                match_string = queued.get('match_string')

                textutils.output_debug("Testing: " + url + " " + str(queued))
                stats.update_stats(url)

                # Throttle if needed
                #if throttle.get_throttle() > 0:
                 #   sleep(throttle.get_throttle())

                # Fetch the target url
                timeout = False
                if match_string:
                    response_code, content, headers = self.fetcher.fetch_url(url, conf.user_agent, conf.fetch_timeout_secs, limit_len=False)
                else:
                    response_code, content, headers = self.fetcher.fetch_url(url, conf.user_agent, conf.fetch_timeout_secs)

                # handle timeout
                if response_code in conf.timeout_codes:
                    handle_timeout(queued, url, self.thread_id, output=self.output)
                    throttle.increase_throttle_delay()
                    timeout = True
                elif response_code in conf.expected_file_responses:
                      # Compare content with generated 404 samples
                    is_valid_result = test_valid_result(content)
                    
                    # If the CRC missmatch, and we have an expected code, we found a valid link
                    if is_valid_result:
                        # Content Test if match_string provided
                        if match_string and re.search(re.escape(match_string), content, re.I):
                            # Add path to valid_path for future actions
                            database.valid_paths.append(queued)
                            textutils.output_found("String-Matched " + description + ' at: ' + conf.target_host + url)
                        elif not match_string:
                            if response_code == 500:
                                textutils.output_found('ISE, ' + description + ' at: ' + conf.target_host + url)    
                            else:
                                textutils.output_found(description + ' at: ' + conf.target_host + url)
                            
                            # Add path to valid_path for future actions
                            database.valid_paths.append(queued)

                # Decrease throttle delay if needed
                if not timeout:	
                    throttle.decrease_throttle_delay()
					
                # Mark item as processed
                stats.update_processed_items()
                database.fetch_queue.task_done()
            except Empty:
                continue



class PrintWorker(Thread):
    """ This worker is used to generate a synchronized non-overlapping console output. """
    def __init__(self):
        Thread.__init__(self)
        self.kill_received = False

    def run(self):
        while not self.kill_received:
            text = database.messages_output_queue.get()
            print(text)
            sys.stdout.flush()
            database.messages_output_queue.task_done()


class PrintResultsWorker(Thread):
    """ This worker is used to generate a synchronized non-overlapping console output for results """
    def __init__(self):
        Thread.__init__(self)
        self.kill_received = False

    def run(self):
        while not self.kill_received:
            text = database.results_output_queue.get()
            print(text)
            sys.stdout.flush()
            database.results_output_queue.task_done()

