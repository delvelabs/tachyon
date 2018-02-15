#!/usr/bin/python3
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

# Ensure python3 runtime
import atexit
import sys

if sys.version_info[0] < 3:
    print("Must be using Python 3")
    sys.exit()

import uuid
import urllib3
import os
import sys
from socket import gaierror
from urllib3 import HTTPConnectionPool, HTTPSConnectionPool
from urllib3.poolmanager import ProxyManager
from datetime import datetime
from hammertime import HammerTime
from hammertime.rules import DetectSoft404, RejectStatusCode, SetHeader, DynamicTimeout, FollowRedirects

sys.path.pop(0)

import tachyon.core.conf as conf
import tachyon.core.database as database
import tachyon.core.dnscache as dnscache
import tachyon.core.loaders as loaders
import tachyon.core.textutils as textutils
import tachyon.core.netutils as netutils
from tachyon.core.fetcher import Fetcher
from tachyon.core.workers import PrintWorker, PrintResultsWorker, JSONPrintResultWorker, FetchCrafted404Worker
from tachyon.core.threads import ThreadManager
from tachyon.plugins import host, file
from tachyon.core.generator import PathGenerator, FileGenerator
from tachyon.core.directoryfetcher import DirectoryFetcher
from tachyon.core.filefetcher import FileFetcher


def load_target_paths(running_path):
    """ Load the target paths in the database """
    textutils.output_info('Loading target paths')
    database.paths += loaders.load_json_resource('paths')


def load_target_files(running_path):
    """ Load the target files in the database """
    textutils.output_info('Loading target files')
    database.files += loaders.load_json_resource('files')


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


def test_paths_exists(hammertime):
    """
    Test for path existence using http codes and computed 404
    Turn off output for now, it would be irrelevant at this point.
    """

    path_generator = PathGenerator()
    loop = hammertime.loop

    paths_to_fetch = path_generator.generate_paths(use_valid_paths=False)
    textutils.output_debug('Cached: ' + str(database.path_cache))

    async def fetch_paths(paths):
        fetcher = DirectoryFetcher(conf.base_url, hammertime)
        await fetcher.fetch_paths(paths)

    textutils.output_info('Probing %d paths' % len(paths_to_fetch))
    loop.run_until_complete(fetch_paths(paths_to_fetch))

    recursion_depth = 0
    if conf.recursive:
        while recursion_depth < conf.recursive_depth_limit:
            recursion_depth += 1
            paths_to_fetch = path_generator.generate_paths(use_valid_paths=True)
            loop.run_until_complete(fetch_paths(paths_to_fetch))
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
        plugin = __import__("tachyon.plugins.host." + plugin_name, fromlist=[plugin_name])
        if hasattr(plugin, 'execute'):
            plugin.execute()


def load_execute_file_plugins():
    """ Import and run path plugins """
    textutils.output_info('Executing ' + str(len(file.__all__)) + ' file plugins')
    for plugin_name in file.__all__:
        plugin = __import__("tachyon.plugins.file." + plugin_name, fromlist=[plugin_name])
        if hasattr(plugin, 'execute'):
            plugin.execute()


def test_file_exists(hammertime):
    """ Test for file existence using http codes and computed 404 """
    async def fetch():
        fetcher = FileFetcher(conf.base_url, hammertime)
        await fetcher.fetch_files(database.valid_paths)
    generator = FileGenerator()
    database.valid_paths = generator.generate_files()
    textutils.output_info('Probing ' + str(len(database.valid_paths)) + ' files')
    if len(database.valid_paths) > 0:
        hammertime.heuristics.add(RejectStatusCode({401, 403}))
        hammertime.loop.run_until_complete(fetch())


def print_program_header():
    """ Print a _cute_ program header """
    print("\n\t Tachyon v" + conf.version + " - Fast Multi-Threaded Web Discovery Tool")
    print("\t https://github.com/delvelabs/tachyon\n")


def configure_hammertime():
    hammertime = HammerTime(retry_count=3, proxy=conf.proxy_url)
    cookies = conf.cookies if conf.cookies else database.session_cookie

    #  Make sure rejecting 404 does not conflict with tomcat fake 404 detection.
    heuristics = [RejectStatusCode({404}), DetectSoft404(), DynamicTimeout(0.05, 5), FollowRedirects()]
    if cookies:
        heuristics.append(SetHeader(name="Cookie", value=cookies))
    hammertime.heuristics.add_multiple(heuristics)
    return hammertime


def main():
    # Get running path
    running_path = os.path.dirname(os.path.realpath(sys.argv[0]))

    # Benchmark
    start_scan_time = datetime.now()

    # Parse command line
    from tachyon.core.arguments import generate_options, parse_args

    parser = generate_options()
    options, args = parse_args(parser, sys.argv)

    if not conf.eval_output and not conf.json_output:
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
    textutils.output_debug(
        "Parsed: " + parsed_host + " port: " + str(parsed_port) + " " + parsed_path + " SSL:" + str(is_ssl))

    # Set conf values
    conf.target_host = parsed_host
    conf.target_base_path = parsed_path
    conf.is_ssl = is_ssl

    if is_ssl and parsed_port == 80:
        conf.target_port = 443
    else:
        conf.target_port = parsed_port

    conf.scheme = 'https' if is_ssl else 'http'
    port = "" if (is_ssl and conf.target_port == 443) or (
    not is_ssl and conf.target_port == 80) else ":%s" % conf.target_port
    conf.base_url = "%s://%s%s" % (conf.scheme, parsed_host, port)

    textutils.output_debug('Version: ' + str(conf.version))
    textutils.output_debug('Max timeouts per url: ' + str(conf.max_timeout_count))
    textutils.output_debug('Worker threads: ' + str(conf.thread_count))
    textutils.output_debug('Target Host: ' + str(conf.target_host))
    textutils.output_debug('Using Tor: ' + str(conf.use_tor))
    textutils.output_debug('Eval-able output: ' + str(conf.eval_output))
    textutils.output_debug('JSON output: ' + str(conf.json_output))
    textutils.output_debug('Using User-Agent: ' + str(conf.user_agent))
    textutils.output_debug('Search only for files: ' + str(conf.files_only))
    textutils.output_debug('Search only for subdirs: ' + str(conf.directories_only))

    if conf.proxy_url:
        textutils.output_debug('Using proxy: ' + str(conf.proxy_url))

    textutils.output_info('Starting Discovery on ' + conf.base_url)

    if conf.use_tor:
        textutils.output_info('Using Tor, be patient it WILL be slow!')
        textutils.output_info('Max timeout count and url fetch timeout doubled for the occasion ;)')
        conf.max_timeout_count *= 2
        conf.fetch_timeout_secs *= 2

    # Handle keyboard exit before multi-thread operations
    print_results_worker = None
    try:
        # Resolve target host to avoid multiple dns lookups
        if not conf.proxy_url:
            resolved, port = dnscache.get_host_ip(conf.target_host, conf.target_port)

        # disable urllib'3 SSL warning (globally)
        urllib3.disable_warnings()

        # Benchmark target host
        if conf.proxy_url:
            database.connection_pool = ProxyManager(conf.proxy_url, timeout=conf.fetch_timeout_secs,
                                                    maxsize=conf.thread_count, block=True, cert_reqs='CERT_NONE')
        elif not conf.proxy_url and is_ssl:
            database.connection_pool = HTTPSConnectionPool(resolved, port=str(port), timeout=conf.fetch_timeout_secs,
                                                           block=True, maxsize=conf.thread_count)
        else:
            database.connection_pool = HTTPConnectionPool(resolved, port=str(port), timeout=conf.fetch_timeout_secs,
                                                          block=True, maxsize=conf.thread_count)

        # Vhost forgery
        if conf.forge_vhost != '<host>':
            conf.target_host = conf.forge_vhost

        if conf.json_output:
            SelectedPrintWorker = JSONPrintResultWorker
        else:
            SelectedPrintWorker = PrintResultsWorker


        # Register cleanup functions to be executed at program exit
        def finish_output():
            # Close program and flush all the output queues.
            try:
                database.results_output_queue.join()
                database.messages_output_queue.join()

                if print_results_worker and 'finalize' in dir(print_results_worker):
                    print_results_worker.finalize()
            except KeyboardInterrupt:
                pass


        # Register cleanup function
        atexit.register(finish_output)

        # Select working modes
        get_session_cookies()
        hammertime = configure_hammertime()
        root_path = ''
        if conf.files_only:

            # 0. Sample /uuid to figure out what is a classic 404 and set value in database
            sample_root_404()
            # Add root to targets
            root_path = conf.path_template.copy()
            root_path['url'] = ''
            database.valid_paths.append(root_path)
            load_target_files(running_path)
            load_execute_host_plugins()
            sample_404_from_found_path()
            load_execute_file_plugins()
            textutils.output_info('Probing ' + str(len(database.valid_paths)) + ' files')
            database.messages_output_queue.join()
            # Start print result worker.
            print_results_worker = SelectedPrintWorker()
            print_results_worker.daemon = True
            print_results_worker.start()
            test_file_exists(hammertime)
        elif conf.directories_only:
            # 0. Sample /uuid to figure out what is a classic 404 and set value in database
            sample_root_404()
            root_path = conf.path_template.copy()
            root_path['url'] = '/'
            database.paths.append(root_path)
            database.valid_paths.append(root_path)
            load_execute_host_plugins()
            print_results_worker = SelectedPrintWorker()
            print_results_worker.daemon = True
            print_results_worker.start()
            load_target_paths(running_path)
            test_paths_exists(hammertime)
        elif conf.plugins_only:
            database.connection_pool = HTTPConnectionPool(resolved, timeout=conf.fetch_timeout_secs, maxsize=1)
            # Add root to targets
            root_path = conf.path_template.copy()
            root_path['url'] = '/'
            database.paths.append(root_path)
            load_execute_host_plugins()
        else:
            # 0. Sample /uuid to figure out what is a classic 404 and set value in database
            # Add root to targets
            root_path = conf.path_template.copy()
            root_path['url'] = '/'
            database.paths.append(root_path)
            load_target_paths(running_path)
            load_target_files(running_path)
            # Execute all Host plugins
            load_execute_host_plugins()
            test_paths_exists(hammertime)
            textutils.output_info('Sampling 404 for new paths')
            textutils.output_info('Generating file targets')
            load_execute_file_plugins()
            database.messages_output_queue.join()
            print_results_worker = SelectedPrintWorker()
            print_results_worker.daemon = True
            print_results_worker.start()
            test_file_exists(hammertime)

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

    sys.exit(0)


if __name__ == "__main__":
    main()
