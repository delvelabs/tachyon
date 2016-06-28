from __future__ import print_function
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
from datetime import datetime
from difflib import SequenceMatcher
from threading import Thread
import json
try:
    from Queue import Empty
except ImportError:
    from queue import Empty
try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse

from core import database, conf, stats, textutils
from core.fetcher import Fetcher


def compute_request_time(start_time, end_time):
    """
     Compute the average request time and set pessimistically (math.ceil) the request timeout value based on it
     This call will mostly decrease the timeout time.
    """
    # Adjust dynamic timeout level:
    completed_time = (end_time - start_time).seconds
    textutils.output_debug("Completed in: " + str(completed_time))

    database.latest_successful_request_time = completed_time + 1

    # We still need to have a max timeout in seconds
    if database.latest_successful_request_time > conf.max_timeout_secs:
        database.latest_successful_request_time = conf.max_timeout_secs
    elif database.latest_successful_request_time < 1:
        database.latest_successful_request_time = 1

    textutils.output_debug("+Ajusted timeout to: " + str(database.latest_successful_request_time))


def handle_timeout(queued, url, thread_id, output=True):
    """ Handle timeout operation for workers """
    if database.latest_successful_request_time > conf.max_timeout_secs:
        database.latest_successful_request_time = conf.max_timeout_secs
    else:
        database.latest_successful_request_time += 1

    textutils.output_debug("-Ajusted timeout to: " + str(database.latest_successful_request_time))

    if not queued['timeout_count']:
        queued['timeout_count'] = 0

    if queued.get('timeout_count') < conf.max_timeout_count:
        new_timeout_count = queued.get('timeout_count') + 1
        queued['timeout_count'] = new_timeout_count
        textutils.output_debug('Thread #' + str(thread_id) + ': re-queuing ' + str(queued))

        # Add back the timed-out item
        database.fetch_queue.put(queued)
    elif output and not database.kill_received:
        # We definitely timed out
        textutils.output_timeout(queued.get('description') + ' at ' + url)

    # update stats
    database.total_timeouts += 1


def handle_redirects(queued, target):
    """ This call is used to determine if a suggested redirect is valid.
    if it happens to be, we change the url entry with the redirected location and add it back
    to the call stack. """
    retry_count = queued.get('retries')
    if retry_count and retry_count > 1:
        return
    elif not retry_count:
        queued['retries'] = 0

    parsed_taget = urlparse(target)
    target_path = parsed_taget.path

    source_path = conf.target_base_path + queued.get('url')
    textutils.output_debug("Handling redirect from: " + source_path + " to " + target_path)

    matcher = SequenceMatcher(isjunk=None, a=target_path, b=source_path, autojunk=False)
    if matcher.ratio() > 0.8:
        queued['url'] = target_path
        queued['retries'] += 1
        # Add back the timed-out item
        textutils.output_debug("Following redirect! " + str(matcher.ratio()))
        database.fetch_queue.put(queued)
    else:
        textutils.output_debug("Bad redirect! " + str(matcher.ratio()))


# If we can speed up this, the whole app will benefit from it.
def test_valid_result(content, is_file=False):
    is_valid_result = True

    # Encoding edge case
    # Must be a string to be compared to the 404 fingerprint
    if not isinstance(content, str):
        content = content.decode('utf-8', 'ignore')

    if not len(content):
        content = ""  # empty file, still a forged 404
    elif len(content) < conf.file_sample_len:
        content = content[0:len(content) - 1]
    else:
        content = content[0:conf.file_sample_len - 1]

    # False positive cleanup for some edge cases
    content = content.strip('\r\n ')

    # Test signatures
    for fingerprint in database.crafted_404s:
        textutils.output_debug("Testing [" + content + "]" + " against Fingerprint: [" + fingerprint + "]")
        matcher = SequenceMatcher(isjunk=None, a=fingerprint, b=content, autojunk=False)

        textutils.output_debug("Ratio " + str(matcher.ratio()))

        # This content is almost similar to a generated 404, therefore it's a 404.
        if matcher.ratio() > 0.8:
            textutils.output_debug("False positive detected!")
            is_valid_result = False
            break

    # An empty file could be a proof of a hidden structure
    if is_file and content == "":
        is_valid_result = True

    return is_valid_result


def detect_tomcat_fake_404(content):
    """ An apache setup will issue a 404 on an existing path if theres a tomcat trying to handle jsp on the same host """
    if content.find(b'Apache Tomcat/') != -1:
        return True

    return False


def test_behavior(content):
    """ Test if a given valid hit has an improbable behavior. Mainly, no url should have the same return content
    As the previous one if it's already deemed valid by the software (non error, unique content)
    Some identical content should be expected during the runtime, but not the same in X consecutive hits"""

    # Assume normal behavior
    normal = True
    textutils.output_debug('Testing behavior')

    if not isinstance(content, str):
        content = content.decode('utf-8', 'ignore')

    if len(database.behavioral_buffer) <= (conf.behavior_queue_size-1):
        database.behavioral_buffer.append(content)

    # If the queue is full, start to test. if not, the system will let a "chance" to the entries.
    if len(database.behavioral_buffer) >= conf.behavior_queue_size:
        textutils.output_debug('Testing for sameness with bufsize:' + str(len(database.behavioral_buffer)))
        # Check if all results in the buffer are the same
        same = all(SequenceMatcher(isjunk=None, a=content, b=saved_content, autojunk=False).ratio() > 0.80
                   for saved_content in database.behavioral_buffer)
        if same:
            textutils.output_debug('Same!')
            normal = False

    # Kick out only the first item in the queue if the queue is full so we can detect if behavior restores
    if not normal and len(database.behavioral_buffer):
        database.behavioral_buffer.pop(0)

    return normal


def reset_behavior_database():
    database.behavioral_buffer = list()


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
                start_time = datetime.now()
                response_code, content, headers = self.fetcher.fetch_url(url, conf.user_agent, database.latest_successful_request_time)
                end_time = datetime.now()

                # Handle fetch timeouts by re-adding the url back to the global fetch queue
                # if timeout count is under max timeout count
                if response_code is 0 or response_code is 500:
                    handle_timeout(queued, url, self.thread_id, output=self.output)
                elif response_code in conf.expected_file_responses:
                    # Encoding edge case
                    # Must be a string to be compared to the 404 fingerprint
                    if not isinstance(content, str):
                        content = content.decode('utf-8', 'ignore')

                    # The server responded with whatever code but 404 or invalid stuff (500). We take a sample
                    if len(content) < conf.file_sample_len:
                        crafted_404 = content[0:len(content) - 1]
                    else:
                        crafted_404 = content[0:conf.file_sample_len - 1]

                    crafted_404 = crafted_404.strip('\r\n ')
                    database.crafted_404s.append(crafted_404)

                    # Exception case for root 404, since it's used as a model for other directories
                    textutils.output_debug("Computed and saved a sample 404 for: " + str(queued) + ": " + crafted_404)
                elif response_code in conf.redirect_codes:
                    if queued.get('handle_redirect', True):
                        location = headers.get('location')
                        if location:
                            handle_redirects(queued, location)

                # Stats
                if response_code not in conf.timeout_codes:
                    stats.update_processed_items()
                    compute_request_time(start_time, end_time)

                # Dequeue item
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
        reset_behavior_database()

    def run(self):
        while not self.kill_received:
            try:
                queued = database.fetch_queue.get(False)
                url = conf.target_base_path + queued.get('url')
                description = queued.get('description')
                textutils.output_debug("Testing directory: " + url + " " + str(queued))

                stats.update_stats(url)

                # Add trailing / for paths
                if not url.endswith('/') and url != '/':
                    url += '/'

                # Fetch directory
                start_time = datetime.now()
                response_code, content, headers = self.fetcher.fetch_url(url, conf.user_agent, database.latest_successful_request_time, limit_len=False)
                end_time = datetime.now()

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
                elif response_code == 404 and detect_tomcat_fake_404(content):
                    database.valid_paths.append(queued)
                    textutils.output_found('Tomcat redirect, ' + description + ' at: ' + conf.target_host + url, {
                        "description": description,
                        "url": conf.base_url + url,
                        "code": response_code,
                        "special": "tomcat-redirect",
                        "severity": queued.get('severity'),
                    })
                elif response_code in conf.expected_path_responses:
                    # Compare content with generated 404 samples
                    is_valid_result = test_valid_result(content)

                    if is_valid_result:
                        # Test if behavior is ok.
                        normal_behavior = test_behavior(content)
                    else:
                        # We don't compute behavior on invalid results
                        normal_behavior = True

                    if normal_behavior and database.behavior_error:
                        textutils.output_info('Normal behavior seems to be restored.')
                        database.behavior_error = False

                    if is_valid_result and not normal_behavior:
                        # We don't declare a behavior change until the current hit has exceeded the maximum
                        # chances it can get.
                        if not database.behavior_error and queued.get('behavior_chances', 0) >= conf.max_behavior_tries:
                            textutils.output_info('Behavior change detected! Results may '
                                                  'be incomplete or tachyon may never exit.')
                            textutils.output_debug('Chances taken: ' + str(queued.get('behavior_chances', 0)))
                            textutils.output_debug(queued.get('url'))
                            database.behavior_error = True

                    # If we find a valid result but the behavior buffer is not full, we give a chance to the
                    # url and increase it's chances count. We consider this a false behavior test.
                    # We do this since an incomplete behavior buffer could give false positives
                    # Additionally, if the fetch queue is empty and we're still not in global behavior error, we
                    # consider all the remaining hits as valid, as they are hits that were given a chance.
                    if is_valid_result and len(database.behavioral_buffer) < conf.behavior_queue_size \
                            and not database.behavior_error and database.fetch_queue.qsize() != 0:
                        if not queued.get('behavior_chances'):
                            queued['behavior_chances'] = 1
                        else:
                            queued['behavior_chances'] += 1

                        if queued['behavior_chances'] < conf.max_behavior_tries:
                            textutils.output_debug('Time for a chance')
                            textutils.output_debug('Chance left to target ' + queued.get('url') + ', re-queuing ' +
                                                   ' qsize: ' + str(database.fetch_queue.qsize()) +
                                                   ' chances: ' + str(queued.get('behavior_chances')))
                            database.fetch_queue.put(queued)
                        else:
                            textutils.output_debug('Chances count busted! ' + queued.get('url') +
                                                   ' qsize: ' + str(database.fetch_queue.qsize()))

                    elif response_code == 401:
                        # Output result, but don't keep the url since we can't poke in protected folder
                        textutils.output_found('Password Protected - ' + description + ' at: ' + conf.target_host + url, {
                            "description": description,
                            "url": conf.base_url + url,
                            "code": response_code,
                            "severity": queued.get('severity'),
                        })
                    # At this point, we have a valid result and the behavioral buffer is full.
                    # The behavior of the hit has been taken in account and the app is not in global behavior error
                    elif is_valid_result:
                        # Add path to valid_path for future actions
                        database.valid_paths.append(queued)

                        # If we reach this point, all edge-cases should be handled and all subsequent requests
                        # should be benchmarked against this new behavior
                        reset_behavior_database()

                        if response_code == 500:
                            textutils.output_found('ISE, ' + description + ' at: ' + conf.target_host + url, {
                                "description": description,
                                "url": conf.base_url + url,
                                "code": response_code,
                                "severity": queued.get('severity'),
                            })
                        elif response_code == 403:
                            textutils.output_found('*Forbidden* ' + description + ' at: ' + conf.target_host + url, {
                                "description": description,
                                "url": conf.base_url + url,
                                "code": response_code,
                                "severity": queued.get('severity'),
                            })
                        else:
                            textutils.output_found(description + ' at: ' + conf.target_host + url, {
                                "description": description,
                                "url": conf.base_url + url,
                                "code": response_code,
                                "severity": queued.get('severity'),
                            })

                elif response_code in conf.redirect_codes:
                    if queued.get('handle_redirect', True):
                        location = headers.get('location')
                        if location:
                            handle_redirects(queued, location)

                # Stats
                if response_code not in conf.timeout_codes:
                    stats.update_processed_items()
                    compute_request_time(start_time, end_time)

                # Mark item as processed
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
        reset_behavior_database()

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

                # Fetch the target url
                start_time = datetime.now()
                if match_string:
                    response_code, content, headers = self.fetcher.fetch_url(url, conf.user_agent, database.latest_successful_request_time, limit_len=False)
                    # Make sure we always match string against a string content
                    if not isinstance(content, str):
                        content = content.decode('utf-8', 'ignore')
                else:
                    response_code, content, headers = self.fetcher.fetch_url(url, conf.user_agent, database.latest_successful_request_time)
                end_time = datetime.now()

                # handle timeout
                if response_code in conf.timeout_codes:
                    handle_timeout(queued, url, self.thread_id, output=self.output)
                elif response_code == 500:
                    textutils.output_found('ISE, ' + description + ' at: ' + conf.target_host + url, {
                        "description": description,
                        "url": conf.base_url + url,
                        "code": response_code,
                        "severity": queued.get('severity'),
                    })
                elif response_code in conf.expected_file_responses:
                    # Test if result is valid
                    is_valid_result = test_valid_result(content, is_file=True)

                    if is_valid_result:
                        # Test if behavior is ok.
                        normal_behavior = test_behavior(content)
                        textutils.output_debug('Normal behavior ' + str(normal_behavior) + ' ' + str(response_code))
                    else:
                        normal_behavior = True

                    # Reset behavior chance when we detect a new state
                    if normal_behavior and database.behavior_error:
                        textutils.output_info('Normal behavior seems to be restored.')
                        database.behavior_error = False

                    if is_valid_result and not normal_behavior:
                        # Looks like the new behavior is now the norm. It's a false positive.
                        # Additionally, we report a behavior change to the user at this point.
                        if not database.behavior_error:
                            textutils.output_info('Behavior change detected! Results may '
                                                  'be incomplete or tachyon may never exit.')
                            textutils.output_debug('Chances taken: ' + str(queued.get('behavior_chances', 0)))
                            textutils.output_debug(queued.get('url'))
                            database.behavior_error = True

                    # If we find a valid result but the behavior buffer is not full, we give a chance to the
                    # url and increase it's chances count. We consider this a false behavior test.
                    # We do this since an incomplete behavior buffer could give false positives
                    # Additionally, if the fetch queue is empty and we're still not in global behavior error, we
                    # consider all the remaining hits as valid, as they are hits that were given a chance.
                    elif is_valid_result and len(database.behavioral_buffer) < conf.behavior_queue_size \
                            and not database.behavior_error and database.fetch_queue.qsize() != 0:
                        if not queued.get('behavior_chances'):
                            queued['behavior_chances'] = 1
                        else:
                            queued['behavior_chances'] += 1

                        if queued['behavior_chances'] < conf.max_behavior_tries:
                            textutils.output_debug('Chance left to target, re-queuing')
                            database.fetch_queue.put(queued)
                    elif is_valid_result:
                        # Make sure we base our next analysis on that positive hit
                        reset_behavior_database()

                        if len(content) == 0:
                            textutils.output_found('Empty ' + description + ' at: ' + conf.target_host + url, {
                                "description": description,
                                "url": conf.base_url + url,
                                "code": response_code,
                                "severity": queued.get('severity'),
                            })
                        else:
                            textutils.output_found(description + ' at: ' + conf.target_host + url, {
                                "description": description,
                                "url": conf.base_url + url,
                                "code": response_code,
                                "severity": queued.get('severity'),
                            })
                    elif match_string and re.search(re.escape(match_string), content, re.I):
                        textutils.output_found("String-Matched " + description + ' at: ' + conf.target_host + url, {
                            "description": description,
                            "url": conf.base_url + url,
                            "code": response_code,
                            "string": match_string,
                            "severity": queued.get('severity'),
                    })

                elif response_code in conf.redirect_codes:
                    if queued.get('handle_redirect', True):
                        location = headers.get('location')
                        if location:
                            handle_redirects(queued, location)

                # Stats
                if response_code not in conf.timeout_codes:
                    stats.update_processed_items()
                    compute_request_time(start_time, end_time)

                # Mark item as processed
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
            try:
                text = database.messages_output_queue.get(timeout=1)
                if text.endswith('\r'):
                    print(" " * database.last_printed_len, file=sys.stdout, end="\r")
                    print(text, file=sys.stdout, end="\r")
                    database.last_printed_len = len(text)
                else:
                    print(text)
                sys.stdout.flush()
                database.messages_output_queue.task_done()
            except Empty:
                # Since we're waiting for a global kill to exit, this is not an error. We're just waiting
                # for more output.
                continue


class PrintResultsWorker(Thread):
    """ This worker is used to generate a synchronized non-overlapping console output for results """
    def __init__(self):
        Thread.__init__(self)
        self.kill_received = False

    def run(self):
        while not self.kill_received:
            try:
                text = str(database.results_output_queue.get(timeout=1))
                print(text)
                sys.stdout.flush()
                database.results_output_queue.task_done()
            except Empty:
                # Since we're waiting for a global kill to exit, this is not an error. We're just waiting
                # for more output.
                continue

class JSONPrintResultWorker(Thread):
    """ This worker is used to generate a synchronized non-overlapping console output for results """
    def __init__(self):
        Thread.__init__(self)
        self.kill_received = False
        self.data = []

    def run(self):
        while not self.kill_received:
            try:
                entry = database.results_output_queue.get(timeout=1)
                self.data.append(entry)
                database.results_output_queue.task_done()
            except Empty:
                # Since we're waiting for a global kill to exit, this is not an error. We're just waiting
                # for more output.
                continue

    def finalize(self):
        print(json.dumps({
            "from": conf.name,
            "version": conf.version,
            "result": self.data,
        }))
        sys.stdout.flush()
