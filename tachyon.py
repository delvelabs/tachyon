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
from core import conf, database, loaders, utils
from core.workers import FetchUrlWorker, PrintWorker
from optparse import OptionParser
from plugins import host, path
from urlparse import urljoin

def wait_for_idle(workers, queue):
    """ Wait until fetch queue is empty and handle user interrupt """
    while len(workers) > 0:
        try:
            if queue.empty():
                # Wait for all threads to return their state
                queue.join()
                workers = []
        except KeyboardInterrupt:
            utils.output_raw('')
            utils.output_info('Keyboard Interrupt Received, cleaning up threads')
            # Kill remaining workers
            for worker in workers:
                worker.kill_received = True
                if worker is not None and worker.isAlive():
                    worker.join(1)

            sys.exit()

def spawn_workers(count, output=True):
    """ Spawn a given number of workers and return a reference list to them """
    # Keep track of all worker threads
    workers = list()
    for thread_id in range(count):
        worker = FetchUrlWorker(thread_id, output)
        worker.daemon = True
        workers.append(worker)
        worker.start()
    return workers


def main():
    """ Main app logic """
    # Ensure the host is of the right format
    utils.sanitize_config()

    # Load target paths
    utils.output_info('Loading target paths')
    database.paths = loaders.load_targets('data/path.lst')

    # Import and run host plugins
    utils.output_info('Executing ' + str(len(host.__all__)) + ' host plugins')
    for plugin_name in host.__all__:
        plugin = __import__ ("plugins.host." + plugin_name, fromlist=[plugin_name])
        if hasattr(plugin , 'execute'):
             plugin.execute()
    
    # Spawn workers
    if conf.search_files or conf.debug:
        workers = spawn_workers(conf.thread_count, output=False)
    else:
        workers = spawn_workers(conf.thread_count)

    # Fill work queue with fetch list
    utils.output_info('Probing ' + str(len(database.paths)) + ' paths')
    for item in database.paths:
        database.fetch_queue.put(item)

    # Wait for initial valid path lookup
    wait_for_idle(workers, database.fetch_queue)
    utils.output_info('Found ' + str(len(database.valid_paths)) + ' valid paths')

    if conf.debug:
        for item in database.valid_paths:
            utils.output_debug(str(item))

    if conf.search_files:
        # Load target files
        utils.output_info('Loading target files')
        database.files = loaders.load_targets('data/file.lst')

        # Combine files with '/' and all valid paths
        tmp_list = list()
        for file in database.files:
            file_copy = dict(file)
            file_copy['url'] = urljoin(conf.target_host, file_copy['url'])
            tmp_list.append(file_copy)
            for valid_url in database.valid_paths:
                file['url'] = valid_url['url'] + file['url']
                tmp_list.append(file)

        # Fill Valid path with generated urls
        for item in tmp_list:
            database.valid_paths.append(item)

        if conf.debug:
            for item in database.valid_paths:
                utils.output_debug(str(item))

        # Add to valid paths
        # Import and run file plugins
        utils.output_info('Executing ' + str(len(path.__all__)) + ' file plugins')
        for plugin_name in path.__all__:
            plugin = __import__ ("plugins.path." + plugin_name, fromlist=[plugin_name])
            if hasattr(plugin , 'execute'):
                 plugin.execute()

        # Spawn workers
        workers = spawn_workers(conf.thread_count)

        # Fill work queue with fetch list
        utils.output_info('Probing ' + str(len(database.valid_paths)) + ' items...')
        for item in database.valid_paths:
            database.fetch_queue.put(item)

        # Wait for file lookup
        wait_for_idle(workers, database.fetch_queue)


def print_program_header():
    """ Print a _cute_ program header """
    print "\n\t Tachyon - Fast Multi-Threaded Web Discovery Tool"
    print "\t https://github.com/initnull/tachyon\n" 


def generate_options():
    """ Generate command line parser """
    usage_str = "usage: %prog <host> [options]"
    parser = OptionParser(usage=usage_str)
    parser.add_option("-b", action="store_false",
                    dest="blacklist", help="Disable content type blacklisting [default: %default]", default=conf.content_type_blacklist)
    parser.add_option("-d", action="store_true",
                    dest="debug", help="Enable debug [default: %default]", default=conf.debug)
    parser.add_option("-g", action="store_true",
                    dest="use_get", help="Use GET instead of HEAD [default: %default]", default=conf.use_get)
    parser.add_option("-f", action="store_false",
                    dest="search_files", help="Disable file searching [default: %default]", default=conf.search_files)
    parser.add_option("-m", metavar="MAXTIMEOUT", dest="max_timeout",
                    help="Max number of timeouts for a given request [default: %default]", default=conf.max_timeout_count)
    parser.add_option("-p", metavar="TOR", dest="use_tor",
                    help="Use Tor [default: %default]", default=conf.use_tor)
    parser.add_option("-t", metavar="TIMEOUT", dest="timeout", 
                    help="Request timeout [default: %default]", default=conf.fetch_timeout_secs)
    parser.add_option("-w", metavar="WORKERS", dest="workers", 
                    help="Number of worker threads [default: %default]", default=conf.thread_count)
    parser.add_option("-u", metavar="AGENT", dest="user_agent",
                    help="User-agent [default: %default]", default=conf.user_agent)
    return parser
    
    
def parse_args(parser, system_args):
    """ Parse and assign options """
    (options, args) = parser.parse_args(system_args)
    conf.debug = options.debug
    conf.content_type_blacklist = options.blacklist
    conf.use_get = options.use_get
    conf.fetch_timeout_secs = int(options.timeout)
    conf.max_timeout_count = int(options.max_timeout)
    conf.thread_count = int(options.workers)
    conf.user_agent = options.user_agent
    conf.use_tor = options.use_tor
    conf.search_files = options.search_files

    return options, args    


# Entry point
if __name__ == "__main__":
    print_program_header()
    
    # Parse command line
    parser = generate_options()
    options, args = parse_args(parser, sys.argv)

    if len(sys.argv) <= 1:
        parser.print_help()
        print ''
        sys.exit()
   
    conf.target_host = args[1]

    # Spawn synchronized print output worker
    print_worker = PrintWorker()
    print_worker.daemon = True
    print_worker.start()
    
    if conf.debug:
        utils.output_debug('Version: ' + str(conf.version))
        utils.output_debug('Use GET instead of HEAD: ' + str(conf.use_get))
        utils.output_debug('Fetch timeout: ' + str(conf.fetch_timeout_secs))
        utils.output_debug('Max timeouts per url: ' + str(conf.max_timeout_count))
        utils.output_debug('Worker threads: ' + str(conf.thread_count))
        utils.output_debug('Target Host: ' + str(conf.target_host))
        utils.output_debug('Using Tor: ' + str(conf.use_tor))
        utils.output_debug('Content-type Blacklisting: ' + str(conf.content_type_blacklist))
        utils.output_debug('Using User-Agent: ' + str(conf.user_agent))
     
    utils.output_info('Starting Discovery on ' + conf.target_host)

    # Handle keyboard exit before multi-thread operations
    try:
        # Launch main loop
        main()
        # Print all remaining messages
        utils.output_info('Done.\n')
        database.output_queue.join()
    except KeyboardInterrupt:
        utils.output_raw('')
        utils.output_info('Keyboard Interrupt Received')
        database.output_queue.join()
        sys.exit(0)
