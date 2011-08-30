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
from core.workers import PrintWorker, PrintResultsWorker, Compute404CRCWorker, TestPathExistsWorker, TestFileExistsWorker
from core.threads import ThreadManager
from optparse import OptionParser
from plugins import host, file

def load_target_paths():
    """ Load the target paths in the database """
    utils.output_info('Loading target paths')
    database.paths += loaders.load_targets('data/path.lst')   


def load_target_files():
    """ Load the target files in the database """
    utils.output_info('Loading target files')
    database.files += loaders.load_targets('data/file.lst')


def benchmark_root_404():
    """ Get the root 404 CRC, this has to be done as soon as possible since plugins could use this information. """
    manager = ThreadManager()
    utils.output_info('Benchmarking root 404')
    path = dict(conf.path_template)
    path['url'] = '/'
    database.fetch_queue.put(path)
    workers = manager.spawn_workers(1, Compute404CRCWorker)
    manager.wait_for_idle(workers, database.fetch_queue)


def test_paths_exists():
    """ 
    Test for path existence using http codes and computed 404
    Spawn workers and turn off output for now, it would be irrelevant at this point. 
    """
    manager = ThreadManager()
    # Fill work queue with fetch list
    utils.output_info('Probing ' + str(len(database.paths)) + ' paths')
    for path in database.paths:
        database.fetch_queue.put(path)

    # Wait for initial valid path lookup
    workers = manager.spawn_workers(conf.thread_count, TestPathExistsWorker)
    manager.wait_for_idle(workers, database.fetch_queue)

    utils.output_info('Found ' + str(len(database.valid_paths) - 1) + ' valid paths')



def compute_existing_path_404_crc():
    """ For all existing path, compute the 404 CRC so we don't get trapped in a tarpit """
    manager = ThreadManager()
    
    for path in database.valid_paths:
        database.fetch_queue.put(path)

    # Emty valid path database since this code will add every path back with their CRC value added
    database.valid_paths = list()
    workers = manager.spawn_workers(conf.thread_count, Compute404CRCWorker)
    manager.wait_for_idle(workers, database.fetch_queue)

    # print valid path
    for path in database.valid_paths:
        utils.output_debug("Valid path after crc: " + str(path))


def load_execute_host_plugins():
    """ Import and run host plugins """
    utils.output_info('Executing ' + str(len(host.__all__)) + ' host plugins')
    for plugin_name in host.__all__:
        plugin = __import__ ("plugins.host." + plugin_name, fromlist=[plugin_name])
        if hasattr(plugin , 'execute'):
             plugin.execute()


def load_execute_file_plugins():
    """ Import and run path plugins """
    utils.output_info('Executing ' + str(len(file.__all__)) + ' file plugins')
    for plugin_name in file.__all__:
        plugin = __import__ ("plugins.file." + plugin_name, fromlist=[plugin_name])
        if hasattr(plugin , 'execute'):
             plugin.execute()


def add_files_to_paths():
    """ Combine all path, filenames and suffixes to build the target list """
    work_list = list()
    cache_test = dict()
    for path in database.valid_paths:
        # Combine current path with all files and suffixes if enabled
        for filename in database.files:
            if filename.get('no_suffix'):
                new_filename = dict(filename)
                new_filename['is_file'] = True

                if path.get('computed_404_crc') is not None:
                    new_filename['computed_404_crc'] = path.get('computed_404_crc')

                if path['url'] == '/':
                    new_filename['url'] = path['url'] + filename['url']
                else:
                    new_filename['url'] = path['url'] + '/' + filename['url']

                if not cache_test.get(new_filename['url']):
                    work_list.append(new_filename)
                    cache_test[new_filename['url']] = True
                    utils.output_debug("No Suffix file added: " + str(new_filename))

            else :
                for suffix in conf.file_suffixes:
                    new_filename = dict(filename)
                    new_filename['is_file'] = True

                    if path.get('computed_404_crc') is not None:
                        new_filename['computed_404_crc'] = path.get('computed_404_crc')

                    if path['url'] == '/':
                        new_filename['url'] = path['url'] + filename['url'] + suffix
                    else:
                        new_filename['url'] = path['url'] + '/' + filename['url'] + suffix

                    if not cache_test.get(new_filename['url']):
                        work_list.append(new_filename)
                        cache_test[new_filename['url']] = True
                        utils.output_debug("File added: " + str(new_filename))


    # Since we have already output the found directories, replace the valid path list
    database.valid_paths = work_list


def test_file_exists():
    """ Test for file existence using http codes and computed 404 """
    manager = ThreadManager()
    # Fill work queue with fetch list
    for item in database.valid_paths:
        database.fetch_queue.put(item)

    # Wait for initial valid path lookup
    workers = manager.spawn_workers(conf.thread_count, TestFileExistsWorker)
    manager.wait_for_idle(workers, database.fetch_queue)


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
    parser.add_option("-f", action="store_false",
                    dest="search_files", help="Disable file searching [default: %default]", default=True)
    parser.add_option("-p", action="store_true",
                    dest="use_tor", help="Use Tor [default: %default]", default=False)
    parser.add_option("-r", action="store_true",
                    dest="raw_output", help="Raw output [default: %default]", default=False)
    parser.add_option("-m", metavar="MAXTIMEOUT", dest="max_timeout",
                    help="Max number of timeouts for a given request [default: %default]", default=conf.max_timeout_count)               
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
    conf.fetch_timeout_secs = int(options.timeout)
    conf.max_timeout_count = int(options.max_timeout)
    conf.thread_count = int(options.workers)
    conf.user_agent = options.user_agent
    conf.use_tor = options.use_tor
    conf.search_files = options.search_files
    conf.raw_output = options.raw_output
    return options, args    


# Entry point / main application logic
if __name__ == "__main__":
    
    # Parse command line
    parser = generate_options()
    options, args = parse_args(parser, sys.argv)

    if not conf.raw_output:
        print_program_header()
        
    if len(sys.argv) <= 1:
        parser.print_help()
        print ''
        sys.exit()
   
    conf.target_host = args[1]

    # Spawn synchronized print output worker
    print_worker = PrintWorker()
    print_worker.daemon = True
    print_worker.start()

    # Ensure the host is of the right format
    utils.sanitize_config()
    
    utils.output_debug('Version: ' + str(conf.version))
    utils.output_debug('Fetch timeout: ' + str(conf.fetch_timeout_secs))
    utils.output_debug('Max timeouts per url: ' + str(conf.max_timeout_count))
    utils.output_debug('Worker threads: ' + str(conf.thread_count))
    utils.output_debug('Target Host: ' + str(conf.target_host))
    utils.output_debug('Using Tor: ' + str(conf.use_tor))
    utils.output_debug('Raw output: ' + str(conf.raw_output))
    utils.output_debug('Using User-Agent: ' + str(conf.user_agent))

    utils.output_info('Starting Discovery on ' + conf.target_host)
    
    if conf.use_tor:
        utils.output_info('Using Tor, be patient it WILL be slow!')
        utils.output_info('Max timeout count and url fetch timeout doubled for the occasion ;)')
        conf.max_timeout_count *= 2
        conf.fetch_timeout_secs *= 2

    # Handle keyboard exit before multi-thread operations
    try:
        # 0. Pre-test and CRC /uuid to figure out what is a classic 404 and set value in database
        benchmark_root_404()

        # Load the target paths and files
        load_target_paths()
        load_target_files()

        # Execute all Host plugins
        load_execute_host_plugins()

        # Test the existence of all input path (loaded + plugins)
        test_paths_exists()

        # Compute the 404 CRC for every existing path
        compute_existing_path_404_crc()

        # Combine generated filenames with urls
        add_files_to_paths()

        # Execute all path plugins
        load_execute_file_plugins()

        # Clean logs output
        utils.output_info('Probing ' + str(len(database.valid_paths)) + ' files')
        database.messages_output_queue.join()

        # Start print result worker.
        print_results_worker = PrintResultsWorker()
        print_results_worker.daemon = True
        print_results_worker.start()

        # Test all file combination
        test_file_exists()

        # Print all remaining messages
        utils.output_info('Done.\n')
        database.results_output_queue.join()
        database.messages_output_queue.join()
    except KeyboardInterrupt:
        utils.output_message_raw('')
        utils.output_info('Keyboard Interrupt Received')
        database.messages_output_queue.join()
        sys.exit(0)
