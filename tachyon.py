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
from core.workers import PrintWorker, Compute404CRCWorker, TestUrlExistsWorker
from core.threads import wait_for_idle, spawn_workers, clean_workers
from optparse import OptionParser
from plugins import host, path
from urlparse import urljoin

def load_target_paths():
    # Load target path database
    utils.output_info('Loading target paths')
    database.paths += loaders.load_targets('data/path.lst')    
    
    
def benchmark_root_404():
    # Get the root 404 CRC, this has to be done as soon as possible since plugins could use this information.
    utils.output_info('Benchmarking root 404')
    path = dict(conf.path_template)
    path['url'] = '/'
    workers = spawn_workers(1, Compute404CRCWorker)
    database.fetch_queue.put(path)
    wait_for_idle(workers, database.fetch_queue)
  
    
def test_paths_existence():
    # Test for path existence using http codes and computed 404
    # Spawn workers and turn off output for now, it would be irrelevant at this point.
    workers = spawn_workers(conf.thread_count, TestUrlExistsWorker, display_output=False)

    # Fill work queue with fetch list
    utils.output_info('Probing ' + str(len(database.paths)) + ' paths')
    for item in database.paths:
        item['url'] = urljoin(conf.target_host, item['url'])
        database.fetch_queue.put(item)

    # Wait for initial valid path lookup
    wait_for_idle(workers, database.fetch_queue)
    clean_workers(workers)
    utils.output_info('Found ' + str(len(database.valid_paths)) + ' valid paths')


def load_execute_host_plugins():
    # Import and run host plugins
    utils.output_info('Executing ' + str(len(host.__all__)) + ' host plugins')
    for plugin_name in host.__all__:
        plugin = __import__ ("plugins.host." + plugin_name, fromlist=[plugin_name])
        if hasattr(plugin , 'execute'):
             plugin.execute()


def main():
    """ Main app logic """
    # Ensure the host is of the right format
    utils.sanitize_config()

    # 0. Pre-test and CRC /uuid to figure out what is a classic 404 and set value in database
    benchmark_root_404()
    
    # Load the target paths
    load_target_paths()

    # Execute all Host plugins
    load_execute_host_plugins()
    
    # Test the existence of all input path (loaded + plugins)
    test_paths_existence()
    
    # Compute the 404 CRC for existing paths
    
    
    
    database.output_queue.join()
    sys.exit()

    if conf.debug:
        for item in database.valid_paths:
            utils.output_debug(str(item))

    if conf.search_files:
        # Load target files
        utils.output_info('Loading target files')
        database.files = loaders.load_targets('data/file.lst')
        if conf.debug:
            for item in database.files:
                utils.output_debug('Target file added: ' + str(item))

        # Combine files with '/' and all valid paths
        tmp_list = list()
        for file in database.files:
            file_copy = dict(file)
            file_copy['url'] = urljoin(conf.target_host, file_copy['url'])
            if conf.debug:
                utils.output('Adding base target: ' + str(file_copy))
            tmp_list.append(file_copy)

            for valid_url in database.valid_paths:
                file_copy = dict(file)
                file_copy['url'] = valid_url['url'] + file['url']
                if conf.debug:
                    utils.output('Adding combined target: ' + str(file_copy))
                tmp_list.append(file_copy)

        # Fill Valid path with generated urls
        for item in tmp_list:
            database.valid_paths.append(item)

        if conf.debug:
            for item in database.valid_paths:
                utils.output_debug('Path to test: ' + str(item))

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
    parser.add_option("-d", action="store_true",
                    dest="debug", help="Enable debug [default: %default]", default=False)
    parser.add_option("-g", action="store_true",
                    dest="use_head", help="Use HEAD instead of GET (Faster but error-prone) [default: %default]", default=False)
    parser.add_option("-f", action="store_false",
                    dest="search_files", help="Disable file searching [default: %default]", default=True)
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
    conf.use_head = options.use_head
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
        utils.output_debug('Use GET instead of HEAD: ' + str(conf.use_head))
        utils.output_debug('Fetch timeout: ' + str(conf.fetch_timeout_secs))
        utils.output_debug('Max timeouts per url: ' + str(conf.max_timeout_count))
        utils.output_debug('Worker threads: ' + str(conf.thread_count))
        utils.output_debug('Target Host: ' + str(conf.target_host))
        utils.output_debug('Using Tor: ' + str(conf.use_tor))
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
