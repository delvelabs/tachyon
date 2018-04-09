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

import sys
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

from . import database, conf
from .__version__ import __version__


def detect_tomcat_fake_404(content):
    """ An apache setup will issue a 404 on an existing path if theres a tomcat trying to handle jsp on the same host """
    if content.find(b'Apache Tomcat/') != -1:
        return True

    return False


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
            "version": __version__,
            "result": self.data,
        }))
        sys.stdout.flush()
