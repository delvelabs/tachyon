#!/usr/bin/env python
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
import uuid
from core import conf, database, dnscache, loaders, textutils, netutils, dbutils
from core.fetcher import Fetcher
from core.workers import PrintWorker, PrintResultsWorker, FetchCrafted404Worker, TestPathExistsWorker, TestFileExistsWorker
from core.threads import ThreadManager
from optparse import OptionParser
from plugins import host, file
from socket import gaierror
from urllib3 import HTTPConnectionPool, HTTPSConnectionPool
from datetime import datetime

def load_target_paths():
    """ Load the target paths in the database """
    textutils.output_info('Loading target paths')
    database.paths += loaders.load_targets('data/path.lst') 

def load_target_files():
    """ Load the target files in the database """
    textutils.output_info('Loading target files')
    database.files += loaders.load_targets('data/file.lst')

def get_session_cookies():
    """ Fetch initial session cookies """
    textutils.output_info('Fetching session cookie')
    path = conf.path_template.copy()
    path['url'] = '/'

    # Were not using the fetch cache for session cookie sampling
    fetcher = Fetcher()

    code, content, headers = fetcher.fetch_url('/', conf.user_agent, 10)
    if code is 200:
        cookies = headers.get('Set-Cookie')
        if cookies:
            database.session_cookie = cookies

def sample_root_404():
    """ Get the root 404, this has to be done as soon as possible since plugins could use this information. """
    manager = ThreadManager()
    textutils.output_info('Benchmarking root 404')
    
    for ext in conf.crafted_404_extensions:
        random_file = str(uuid.uuid4())
        path = conf.path_template.copy()

        if path['url'] != '/':
            path['url'] = '/' + random_file + ext
        else:
            path['url'] = random_file + ext

        # Were not using the fetch cache for 404 sampling
        database.fetch_queue.put(path)

    # Forced bogus path check
    random_file = str(uuid.uuid4())
    path = conf.path_template.copy()
    path['url'] = '/' + random_file + '/'

    # Were not using the fetch cache for 404 sampling
    database.fetch_queue.put(path)

    workers = manager.spawn_workers(len(conf.crafted_404_extensions), FetchCrafted404Worker)
    manager.wait_for_idle(workers, database.fetch_queue)


def test_paths_exists():
    """ 
    Test for path existence using http codes and computed 404
    Spawn workers and turn off output for now, it would be irrelevant at this point. 
    """
    manager = ThreadManager()
    
    # Fill work queue with fetch list
    for path in database.paths:
        dbutils.add_path_to_fetch_queue(path)

    # Consider some file target as potential path
    for file in database.files:
        if not file.get('no_suffix'):
            file_as_path = file.copy()
            file_as_path['url'] = '/' + file_as_path['url']
            dbutils.add_path_to_fetch_queue(file_as_path)

    done_paths = []
    recursion_depth = 0

    textutils.output_debug('Cached: ' + str(database.path_cache))
    while database.fetch_queue.qsize() > 0:
        textutils.output_info('Probing ' + str(database.fetch_queue.qsize()) + ' paths')
        
        # Wait for initial valid path lookup
        workers = manager.spawn_workers(conf.thread_count, TestPathExistsWorker)
        manager.wait_for_idle(workers, database.fetch_queue)
        recursion_depth += 1
        
        if not conf.recursive:
            break
        
        if recursion_depth >= conf.recursive_depth_limit:
            break    
        
        for validpath in database.valid_paths:
            
            if validpath['url'] == '/' or validpath['url'] in done_paths:
                continue
            
            done_paths.append(validpath['url'])
            
            for path in database.paths:
                if path['url'] in ('/', ''):
                    continue
                path = path.copy()
                path['url'] = validpath['url'] + path['url']
                dbutils.add_path_to_fetch_queue(path)

    textutils.output_info('Found ' + str(len(database.valid_paths)) + ' valid paths')



def sample_404_from_found_path():
    """ For all existing path, compute the 404 CRC so we don't get trapped in a tarpit """
    manager = ThreadManager()
    
    for path in database.valid_paths:
        textutils.output_debug("Path in valid path table: " + str(path))
        for ext in conf.crafted_404_extensions:
            path_clone = path.copy()
            random_file = str(uuid.uuid4())
            
            # We don't benchmark / since we do it first before path discovery
            if path_clone['url'] != '/':
                path_clone['url'] = path_clone['url'] + '/' + random_file + ext
                # Were not using the fetch cache for 404 sampling
                database.fetch_queue.put(path_clone)

    workers = manager.spawn_workers(conf.thread_count, FetchCrafted404Worker)
    manager.wait_for_idle(workers, database.fetch_queue)



def load_execute_host_plugins():
    """ Import and run host plugins """
    textutils.output_info('Executing ' + str(len(host.__all__)) + ' host plugins')
    for plugin_name in host.__all__:
        plugin = __import__ ("plugins.host." + plugin_name, fromlist=[plugin_name])
        if hasattr(plugin , 'execute'):
             plugin.execute()


def load_execute_file_plugins():
    """ Import and run path plugins """
    textutils.output_info('Executing ' + str(len(file.__all__)) + ' file plugins')
    for plugin_name in file.__all__:
        plugin = __import__ ("plugins.file." + plugin_name, fromlist=[plugin_name])
        if hasattr(plugin , 'execute'):
             plugin.execute()


def add_files_to_paths():
    """ Combine all path, filenames and suffixes to build the target list """
    work_list = list()
    for path in database.valid_paths:
        # Combine current path with all files and suffixes if enabled
        for filename in database.files:
            if filename.get('no_suffix'):
                new_filename = filename.copy()
                new_filename['is_file'] = True

                if path['url'] == '/':
                    new_filename['url'] = ''.join([path['url'], filename['url']])
                else:
                    new_filename['url'] = ''.join([path['url'], '/', filename['url']])

                work_list.append(new_filename)
                textutils.output_debug("No Suffix file added: " + str(new_filename))
            elif filename.get('executable'):
                for executable_suffix in conf.executables_suffixes:
                    new_filename = filename.copy()
                    new_filename['is_file'] = True

                    if path['url'] == '/':
                        new_filename['url'] = ''.join([path['url'], filename['url'], executable_suffix])
                    else:
                        new_filename['url'] = ''.join([path['url'], '/', filename['url'], executable_suffix])

                    work_list.append(new_filename)
                    textutils.output_debug("Executable File added: " + str(new_filename))
            else:
                for suffix in conf.file_suffixes:
                    new_filename = filename.copy()
                    new_filename['is_file'] = True

                    if path['url'] == '/':
                        new_filename['url'] = ''.join([path['url'], filename['url'], suffix])
                    else:
                        new_filename['url'] = ''.join([path['url'], '/', filename['url'], suffix])

                    work_list.append(new_filename)
                    textutils.output_debug("Regular File added: " + str(new_filename))

    # Since we have already output the found directories, replace the valid path list
    database.valid_paths = work_list


def test_file_exists():
    """ Test for file existence using http codes and computed 404 """
    manager = ThreadManager()
    # Fill work queue with fetch list
    for item in database.valid_paths:
        dbutils.add_file_to_fetch_queue(item)

    # Wait for initial valid path lookup
    workers = manager.spawn_workers(conf.thread_count, TestFileExistsWorker)
    manager.wait_for_idle(workers, database.fetch_queue)


def print_program_header():
    """ Print a _cute_ program header """
    print("\n\t Tachyon v" + conf.version + " - Fast Multi-Threaded Web Discovery Tool")
    print("\t https://github.com/initnull/tachyon\n") 


def generate_options():
    """ Generate command line parser """
    usage_str = "usage: %prog <host> [options]"
    parser = OptionParser(usage=usage_str)
    parser.add_option("-d", action="store_true",
                    dest="debug", help="Enable debug [default: %default]", default=False)        
    parser.add_option("-f", action="store_true",
                    dest="search_files", help="search only for files [default: %default]", default=False)
    parser.add_option("-s", action="store_true",
                    dest="search_dirs", help="search only for subdirs [default: %default]", default=False)
    parser.add_option("-b", action="store_true",
                    dest="recursive", help="Search for subdirs recursively [default: %default]", default=False)
    parser.add_option("-l", metavar="LIMIT", dest="limit",
                    help="limit recursive depth [default: %default]", default=conf.recursive_depth_limit)
    #parser.add_option("-p", action="store_true",
                   # dest="use_tor", help="Use Tor [default: %default]", default=False)
    parser.add_option("-e", action="store_true",
                    dest="eval_output", help="Eval-able output [default: %default]", default=False)
    parser.add_option("-m", metavar="MAXTIMEOUT", dest="max_timeout",
                    help="Max number of timeouts for a given request [default: %default]", default=conf.max_timeout_count)
    parser.add_option("-w", metavar="WORKERS", dest="workers", 
                    help="Number of worker threads [default: %default]", default=conf.thread_count)
    parser.add_option("-v", metavar="VHOST", dest="forge_vhost",
                    help="forge destination vhost [default: %default]", default='<host>')
    parser.add_option("-z", action="store_true",
                    dest="plugins_only", help="Only run plugins then exit [default: %default]", default=False)
    parser.add_option("-u", metavar="AGENT", dest="user_agent",
                    help="User-agent [default: %default]", default=conf.user_agent)
    parser.add_option("-o", metavar="SUBATOMIC", dest="subatomic",
                    help="Output log to a Subatomic server (ip:port:runid) [default: %default]", default=conf.subatomic)
    return parser
    
    
def parse_args(parser, system_args):
    """ Parse and assign options """
    (options, args) = parser.parse_args(system_args)
    conf.debug = options.debug
    conf.max_timeout_count = int(options.max_timeout)
    conf.thread_count = int(options.workers)
    conf.user_agent = options.user_agent
    #conf.use_tor = options.use_tor
    conf.search_files = options.search_files
    conf.eval_output = options.eval_output
    conf.files_only = options.search_files
    conf.directories_only = options.search_dirs
    conf.recursive = options.recursive
    conf.recursive_depth_limit = int(options.limit)
    conf.forge_vhost = options.forge_vhost
    conf.plugins_only = options.plugins_only
    conf.subatomic = options.subatomic
    return options, args

def test_python_version():
    """ Test python version, return True if version is high enough, False if not """
    if sys.version_info[:2] < (2, 6):
        return False
    else:
        return True
        

# Entry point / main application logic
if __name__ == "__main__":
    # Benchmark
    start_scan_time = datetime.now()
    
    # Test python version
    if not test_python_version():
        print("Your python interpreter is so old it has to wear diapers. Please upgrade to at least 2.6 ;)")
        sys.exit()
        
    # Parse command line
    parser = generate_options()
    options, args = parse_args(parser, sys.argv)

    if not conf.eval_output:
        print_program_header()
        
    if len(sys.argv) <= 1:
        parser.print_help()
        print('')
        sys.exit()
   

    # Spawn synchronized print output worker
    print_worker = PrintWorker()
    print_worker.daemon = True
    print_worker.start()

    # Ensure the host is of the right format and set it in config
    parsed_host, parsed_port, parsed_path, is_ssl = netutils.parse_hostname(args[1])
    textutils.output_debug("Parsed: " + parsed_host + " port: " + str(parsed_port) + " " +  parsed_path + " SSL:" + str(is_ssl))
    
    # Set conf values
    conf.target_host = parsed_host
    conf.target_base_path = parsed_path
    conf.is_ssl = is_ssl
    
    
    textutils.output_debug('Version: ' + str(conf.version))
    textutils.output_debug('Max timeouts per url: ' + str(conf.max_timeout_count))
    textutils.output_debug('Worker threads: ' + str(conf.thread_count))
    textutils.output_debug('Target Host: ' + str(conf.target_host))
    textutils.output_debug('Using Tor: ' + str(conf.use_tor))
    textutils.output_debug('Eval-able output: ' + str(conf.eval_output))
    textutils.output_debug('Using User-Agent: ' + str(conf.user_agent))
    textutils.output_debug('Search only for files: ' + str(conf.files_only))
    textutils.output_debug('Search only for subdirs: ' + str(conf.directories_only))

    textutils.output_info('Starting Discovery on ' + conf.target_host)
    
    if conf.use_tor:
        textutils.output_info('Using Tor, be patient it WILL be slow!')
        textutils.output_info('Max timeout count and url fetch timeout doubled for the occasion ;)')
        conf.max_timeout_count *= 2
        conf.fetch_timeout_secs *= 2

    # Handle keyboard exit before multi-thread operations
    try:
        # Resolve target host to avoid multiple dns lookups
        resolved, port = dnscache.get_host_ip(parsed_host, parsed_port)

        # Benchmark target host
        if is_ssl:
            database.connection_pool = HTTPSConnectionPool(resolved,port=str(port), timeout=conf.fetch_timeout_secs, maxsize=conf.thread_count)
        else:
            database.connection_pool = HTTPConnectionPool(resolved, port=str(port), timeout=conf.fetch_timeout_secs, maxsize=conf.thread_count)

        # Vhost forgery
        if conf.forge_vhost != '<host>':
            conf.target_host = conf.forge_vhost

        root_path = ''
        if conf.files_only:
            get_session_cookies()
            # 0. Sample /uuid to figure out what is a classic 404 and set value in database
            sample_root_404()
            # Add root to targets
            root_path = conf.path_template.copy()
            root_path['url'] = ''
            database.valid_paths.append(root_path)
            load_target_files()
            load_execute_host_plugins()
            sample_404_from_found_path()
            add_files_to_paths()
            load_execute_file_plugins()
            textutils.output_info('Probing ' + str(len(database.valid_paths)) + ' files')
            database.messages_output_queue.join()
            # Start print result worker.
            print_results_worker = PrintResultsWorker()
            print_results_worker.daemon = True
            print_results_worker.start()
            test_file_exists()
        elif conf.directories_only:
            get_session_cookies()
            # 0. Sample /uuid to figure out what is a classic 404 and set value in database
            sample_root_404()
            root_path = conf.path_template.copy()
            root_path['url'] = '/'
            database.paths.append(root_path)
            database.valid_paths.append(root_path)
            load_execute_host_plugins()
            print_results_worker = PrintResultsWorker()
            print_results_worker.daemon = True
            print_results_worker.start()
            load_target_paths()
            test_paths_exists()
        elif conf.plugins_only:
            get_session_cookies()
            database.connection_pool = HTTPConnectionPool(resolved, timeout=conf.fetch_timeout_secs, maxsize=1) 
            # Add root to targets
            root_path = conf.path_template.copy()
            root_path['url'] = '/'
            database.paths.append(root_path) 
            load_execute_host_plugins()
        else:
            get_session_cookies()
            # 0. Sample /uuid to figure out what is a classic 404 and set value in database
            sample_root_404()
            # Add root to targets
            root_path = conf.path_template.copy()
            root_path['url'] = '/'
            database.paths.append(root_path)
            load_target_paths()
            load_target_files()
            # Execute all Host plugins
            load_execute_host_plugins()
            test_paths_exists()
            sample_404_from_found_path()
            add_files_to_paths()
            load_execute_file_plugins()
            textutils.output_info('Probing ' + str(len(database.valid_paths)) + ' files')
            database.messages_output_queue.join()
            print_results_worker = PrintResultsWorker()
            print_results_worker.daemon = True
            print_results_worker.start()
            test_file_exists()

        # Benchmark
        end_scan_time = datetime.now()

        # Print all remaining messages
        textutils.output_info('Scan completed in: ' + str(end_scan_time - start_scan_time) + '\n')
        database.results_output_queue.join()
        database.messages_output_queue.join()
    except KeyboardInterrupt:
        textutils.output_raw_message('')
        textutils.output_error('Keyboard Interrupt Received')
    except gaierror:
        textutils.output_error('Error resolving host')


    # Close program
    database.messages_output_queue.join()
    sys.exit(0)


