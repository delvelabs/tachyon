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
from hammertime.rules import RejectStatusCode
from hammertime.rules.deadhostdetection import OfflineHostException

import tachyon.core.conf as conf
import tachyon.core.database as database
import tachyon.core.loaders as loaders
import tachyon.core.textutils as textutils
import tachyon.core.netutils as netutils
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
    header = "\n\t Tachyon v%s - Fast Multi-Threaded Web Discovery Tool\n\t https://github.com/delvelabs/tachyon\n"
    click.echo(header % __version__)


async def scan(hammertime, *, cookies=None, directories_only=False, files_only=False, plugins_only=False, **kwargs):
    if cookies is not None:
        set_cookies(hammertime, cookies)
    else:
        await get_session_cookies(hammertime)

    load_execute_host_plugins()
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
@click.option("-c", "--cookie-file", default="")
@click.option("-l", "--depth-limit", default=2)
@click.option("-s", "--directories-only", is_flag=True)
@click.option("-f", "--files-only", is_flag=True)
@click.option("-j", "--json-output", is_flag=True)
@click.option("-m", "--max-retry-count", default=3)
@click.option("-z", "--plugins-only", is_flag=True)
@click.option("-x", "--plugin-settings", multiple=True)
@click.option("-p", "--proxy", default="")
@click.option("-r", "--recursive", is_flag=True)
@click.option("-u", "--user-agent", default=default_user_agent)
@click.option("-v", "--vhost", type=str, default=None)
@click.argument("target_host")
def main(*, target_host, cookie_file, json_output, max_retry_count, plugin_settings, proxy, user_agent, vhost,
         depth_limit, directories_only, files_only, plugins_only, recursive):

    if json_output:
        conf.json_output = True
    else:
        print_program_header()

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

    textutils.init_log()
    textutils.output_info('Starting Discovery on ' + conf.base_url)

    for option in plugin_settings:
        plugin, value = option.split(':', 1)
        conf.plugin_settings[plugin].append(value)

    try:
        root_path = conf.path_template.copy()
        root_path['url'] = '/'
        database.valid_paths.append(root_path)
        load_target_paths()
        load_target_files()
        conf.cookies = loaders.load_cookie_file(cookie_file)
        conf.user_agent = user_agent
        conf.proxy_url = proxy
        conf.forge_vhost = vhost

        hammertime = configure_hammertime(cookies=conf.cookies, proxy=conf.proxy_url, retry_count=max_retry_count,
                                          user_agent=conf.user_agent, vhost=conf.forge_vhost)
        hammertime.loop.run_until_complete(scan(hammertime, cookies=conf.cookies, directories_only=directories_only,
                                                files_only=files_only, plugins_only=plugins_only,
                                                depth_limit=depth_limit, recursive=recursive))
        # Print all remaining messages
        textutils.output_info('Scan completed in: %.3fs' % hammertime.stats.duration)

    except (KeyboardInterrupt, asyncio.CancelledError):
        textutils.output_error('Keyboard Interrupt Received')
    except OfflineHostException:
        textutils.output_error("Target host seems to be offline.")
    finally:
        textutils.flush()


if __name__ == "__main__":
    main()
