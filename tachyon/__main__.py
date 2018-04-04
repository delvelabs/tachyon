# Tachyon - Fast Multi-Threaded Web Discovery Tool
# Copyright (c) 2011 Gabriel Tremblay - initnull hat gmail.com
# Copyright (C) 2018-  Delve Labs inc.
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


import asyncio
import click
import sys
from socket import gaierror
from urllib3 import HTTPConnectionPool, HTTPSConnectionPool
from urllib3.poolmanager import ProxyManager
from hammertime.rules import RejectStatusCode
from hammertime.rules.deadhostdetection import OfflineHostException

import tachyon.core.conf as conf
import tachyon.core.database as database
import tachyon.core.dnscache as dnscache
import tachyon.core.loaders as loaders
import tachyon.core.textutils as textutils
import tachyon.core.netutils as netutils
from tachyon.core.workers import PrintWorker, PrintResultsWorker, JSONPrintResultWorker
from tachyon.plugins import host, file
from tachyon.core.generator import PathGenerator, FileGenerator
from tachyon.core.directoryfetcher import DirectoryFetcher
from tachyon.core.filefetcher import FileFetcher
from tachyon.core.config import configure_hammertime, set_cookies, default_user_agent
from tachyon.core.__version__ import __version__


def load_target_paths():
    """ Load the target paths in the database """
    textutils.output_info('Loading target paths')
    database.paths += loaders.load_json_resource('paths')


def load_target_files():
    """ Load the target files in the database """
    textutils.output_info('Loading target files')
    database.files += loaders.load_json_resource('files')


async def get_session_cookies(hammertime):
    """ Fetch the root path in a single request so aiohttp will use the returned cookies in all future requests. """
    textutils.output_info('Fetching session cookie')
    path = '/'
    await hammertime.request(conf.base_url + path)


async def test_paths_exists(hammertime, *, recursive=False, depth_limit=2):
    """
    Test for path existence using http codes and computed 404
    Turn off output for now, it would be irrelevant at this point.
    """

    path_generator = PathGenerator()
    fetcher = DirectoryFetcher(conf.base_url, hammertime)

    paths_to_fetch = path_generator.generate_paths(use_valid_paths=False)

    textutils.output_info('Probing %d paths' % len(paths_to_fetch))
    await fetcher.fetch_paths(paths_to_fetch)

    if recursive:
        recursion_depth = 0
        while recursion_depth < depth_limit:
            recursion_depth += 1
            paths_to_fetch = path_generator.generate_paths(use_valid_paths=True)
            await fetcher.fetch_paths(paths_to_fetch)
    textutils.output_info('Found ' + str(len(database.valid_paths)) + ' valid paths')


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


async def test_file_exists(hammertime):
    """ Test for file existence using http codes and computed 404 """
    fetcher = FileFetcher(conf.base_url, hammertime)
    generator = FileGenerator()
    database.valid_paths = generator.generate_files()
    textutils.output_info('Probing ' + str(len(database.valid_paths)) + ' files')
    if len(database.valid_paths) > 0:
        hammertime.heuristics.add(RejectStatusCode({401, 403}))
        await fetcher.fetch_files(database.valid_paths)


def print_program_header():
    """ Print a _cute_ program header """
    return "\n\t Tachyon v" + __version__ + " - Fast Multi-Threaded Web Discovery Tool\n" \
                                              "\t https://github.com/delvelabs/tachyon\n"


async def scan(hammertime, *, cookies=None, directories_only=False, files_only=False, plugins_only=False, **kwargs):
    if cookies is not None:
        set_cookies(hammertime, cookies)
    else:
        await get_session_cookies(hammertime)

    #load_execute_host_plugins()
    if not plugins_only:
        if not files_only:
            await test_paths_exists(hammertime, **kwargs)
        if not directories_only:
            textutils.output_info('Generating file targets')
            load_execute_file_plugins()
            database.messages_output_queue.join()
            await test_file_exists(hammertime)


def finish_output(print_worker):
    # flush all the output queues.
    try:
        database.results_output_queue.join()
        database.messages_output_queue.join()
        if print_worker and 'finalize' in dir(print_worker):
            print_worker.finalize()
    except KeyboardInterrupt:
        pass


@click.command()
@click.option("--cookie-file", default="")
@click.option("--depth-limit", default=2)
@click.option("--directories-only", is_flag=True)
@click.option("--files-only", is_flag=True)
@click.option("--json-output", is_flag=True)
@click.option("--max-retry-count", default=3)
@click.option("--plugins-only", is_flag=True)
@click.option("--proxy", default="")
@click.option("--recursive", is_flag=True)
@click.option("--user-agent", default=default_user_agent)
@click.option("--vhost", type=str, default=None)
@click.argument("target_host")
def main(target_host, cookie_file, json_output, max_retry_count,
         proxy, user_agent, vhost, **kwargs):

    click.echo(print_program_header())
    # Spawn synchronized print output worker
    print_worker = PrintWorker()
    print_worker.daemon = True
    print_worker.start()

    # Ensure the host is of the right format and set it in config
    parsed_host, parsed_port, parsed_path, is_ssl = netutils.parse_hostname(target_host)
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

    textutils.output_info('Starting Discovery on ' + conf.base_url)

    # Handle keyboard exit before multi-thread operations
    print_results_worker = None
    try:
        # Resolve target host to avoid multiple dns lookups
        if not proxy:
            resolved, port = dnscache.get_host_ip(conf.target_host, conf.target_port)

        # Benchmark target host
        if proxy:
            database.connection_pool = ProxyManager(proxy, timeout=conf.fetch_timeout_secs,
                                                    maxsize=conf.thread_count, block=True, cert_reqs='CERT_NONE')
        elif not proxy and is_ssl:
            database.connection_pool = HTTPSConnectionPool(resolved, port=str(port), timeout=conf.fetch_timeout_secs,
                                                           block=True, maxsize=conf.thread_count)
        else:
            database.connection_pool = HTTPConnectionPool(resolved, port=str(port), timeout=conf.fetch_timeout_secs,
                                                          block=True, maxsize=conf.thread_count)

        print_results_worker = JSONPrintResultWorker() if json_output else PrintResultsWorker()
        print_results_worker.daemon = True
        print_results_worker.start()

        root_path = conf.path_template.copy()
        root_path['url'] = '/'
        database.valid_paths.append(root_path)
        load_target_paths()
        load_target_files()
        cookies = loaders.load_cookie_file(cookie_file)

        hammertime = configure_hammertime(cookies=cookies, proxy=proxy, retry_count=max_retry_count,
                                          user_agent=user_agent, vhost=vhost)
        hammertime.loop.run_until_complete(scan(hammertime, cookies=cookies, **kwargs))
        # Print all remaining messages
        textutils.output_info('Scan completed in: %.3fs\n' % hammertime.stats.duration)
        database.results_output_queue.join()
        database.messages_output_queue.join()

    except (KeyboardInterrupt, asyncio.CancelledError):
        textutils.output_raw_message('')
        textutils.output_error('Keyboard Interrupt Received')
    except gaierror:
        textutils.output_error('Error resolving host')
    except OfflineHostException:
        textutils.output_error("Target host seems to be offline.")
    finally:
        if print_results_worker is not None:
            finish_output(print_results_worker)


if __name__ == "__main__":
    main()
