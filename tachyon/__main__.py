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
from urllib.parse import urlparse

import click
import tachyon.database as database
import tachyon.loaders as loaders
import tachyon.textutils as textutils
from hammertime.http import Entry
from hammertime.rules import RejectStatusCode
from hammertime.rules.deadhostdetection import OfflineHostException
from hammertime.rules.redirects import RejectRedirection
from hammertime.rules.simhash import Simhash
from hammertime.ruleset import RejectRequest, StopRequest
from tachyon.directoryfetcher import DirectoryFetcher
from tachyon.filefetcher import FileFetcher

import tachyon.conf as conf
from tachyon.config import configure_hammertime, set_cookies, default_user_agent, custom_event_loop
from tachyon.generator import PathGenerator, FileGenerator
from tachyon.plugins import host, file
from tachyon.result import ResultAccumulator


def load_target_paths():
    """ Load the target paths in the database """
    textutils.output_info('Loading target paths')
    database.paths += loaders.load_json_resource('paths')


def load_target_files():
    """ Load the target files in the database """
    textutils.output_info('Loading target files')
    database.files += loaders.load_json_resource('files')


async def get_session_cookies(hammertime):
    try:
        """ Fetch the root path in a single request so aiohttp will use the returned cookies in all future requests. """
        textutils.output_info('Fetching session cookie')
        path = '/'
        await hammertime.request(conf.base_url + path)
    except RejectRequest:
        textutils.output_info('Request for website root failed.')


async def test_paths_exists(hammertime, *, recursive=False, depth_limit=2, accumulator):
    """
    Test for path existence using http codes and computed 404
    Turn off output for now, it would be irrelevant at this point.
    """

    check_closed(hammertime)

    path_generator = PathGenerator()
    fetcher = DirectoryFetcher(conf.base_url, hammertime, accumulator=accumulator)

    paths_to_fetch = path_generator.generate_paths(use_valid_paths=False)

    if len(paths_to_fetch) > 0:
        textutils.output_info('Probing %d paths' % len(paths_to_fetch))

    await fetcher.fetch_paths(paths_to_fetch)

    if recursive:
        recursion_depth = 0
        while recursion_depth < depth_limit:
            recursion_depth += 1
            paths_to_fetch = path_generator.generate_paths(use_valid_paths=True)
            await fetcher.fetch_paths(paths_to_fetch)

    count = len(database.valid_paths) - 1  # Removing one as it is the root path
    textutils.output_info('Found %d valid paths' % count)


async def load_execute_host_plugins(hammertime):
    """ Import and run host plugins """
    count = len(host.__all__)
    if count == 0:
        return

    textutils.output_info('Executing %d host plugins' % count)
    for plugin_name in host.__all__:
        plugin = __import__("tachyon.plugins.host." + plugin_name, fromlist=[plugin_name])
        if hasattr(plugin, 'execute'):
            await plugin.execute(hammertime)


def load_execute_file_plugins():
    """ Import and run path plugins """
    count = len(file.__all__)
    if count == 0:
        return

    textutils.output_info('Executing %d file plugins' % count)
    for plugin_name in file.__all__:
        plugin = __import__("tachyon.plugins.file." + plugin_name, fromlist=[plugin_name])
        if hasattr(plugin, 'execute'):
            plugin.execute()


async def test_file_exists(hammertime, accumulator, skip_root=False):
    """ Test for file existence using http codes and computed 404 """

    check_closed(hammertime)

    fetcher = FileFetcher(conf.base_url, hammertime, accumulator=accumulator)
    generator = FileGenerator()
    files_to_fetch = generator.generate_files(skip_root=skip_root)

    count = len(files_to_fetch)

    textutils.output_info('Probing %d files' % count)
    if len(database.valid_paths) > 0:
        hammertime.heuristics.add(RejectStatusCode({401, 403}))
        await fetcher.fetch_files(files_to_fetch)


def format_stats(stats):
    message = "Statistics: Requested: {}; Completed: {}; Duration: {:.0f} s; Retries: {}; Request rate: {:.2f}"
    return message.format(stats.requested, stats.completed, stats.duration, stats.retries, stats.rate)


def check_closed(hammertime):
    if hammertime.is_closed or getattr(hammertime, "_interrupted", False):
        raise KeyboardInterrupt()


async def drain(hammertime):
    iterator = hammertime.successful_requests()

    # Really make sure we are done (issue in hammertime 0.5.1 when first request is a failure?)
    while iterator.has_pending():
        async for _ in iterator:  # noqa: F841
            pass  # Just drain the pre-probe queries from the queue


async def scan(hammertime, *, accumulator,
               cookies=None, directories_only=False, files_only=False, plugins_only=False,
               **kwargs):

    if cookies is not None:
        set_cookies(hammertime, cookies)
    else:
        await get_session_cookies(hammertime)

    await load_execute_host_plugins(hammertime)

    await drain(hammertime)

    if not plugins_only:
        if not directories_only:
            textutils.output_info('Generating file targets for target root')
            load_execute_file_plugins()
            await test_file_exists(hammertime, accumulator=accumulator)

        if not files_only:
            await test_paths_exists(hammertime, accumulator=accumulator, **kwargs)

            if not directories_only:
                textutils.output_info('Generating file targets')
                load_execute_file_plugins()
                await test_file_exists(hammertime, accumulator=accumulator, skip_root=True)

    check_closed(hammertime)

    validator = ReFetch(hammertime)
    if await validator.is_valid(Entry.create(conf.base_url + "/")):
        textutils.output_info("Re-validating prior results.")
        await accumulator.revalidate(validator)
    else:
        textutils.output_error("Re-validation aborted. Target no longer appears to be up.")

    check_closed(hammertime)


class ReFetch:
    def __init__(self, hammertime):
        self.hammertime = hammertime

    async def is_valid(self, entry):
        value = getattr(entry.result, 'error_simhash', None)
        if value is not None:
            # Revalidate the responses with the known bad behavior signatures.
            current = Simhash(value)
            if any(current.distance(Simhash(k)) < 5 for k in self.hammertime.kb.bad_behavior_response):
                return False

        try:
            await self.hammertime.request(entry.request.url, arguments=entry.arguments)
            return True
        except RejectRedirection:
            # This is most likely the home path check as the result would never reach revalidation otherwise
            return True
        except Exception:
            return False


@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.option("-a", "--allow-download", is_flag=True)
@click.option("-c", "--cookie-file", default="")
@click.option("-l", "--depth-limit", type=int, default=2)
@click.option("-s", "--directories-only", is_flag=True)
@click.option("-f", "--files-only", is_flag=True)
@click.option("-j", "--json-output", is_flag=True)
@click.option("-m", "--max-retry-count", type=int, default=3)
@click.option("-z", "--plugins-only", is_flag=True)
@click.option("-x", "--plugin-settings", multiple=True)
@click.option("-p", "--proxy", default="")
@click.option("-r", "--recursive", is_flag=True)
@click.option("-u", "--user-agent", default=default_user_agent)
@click.option("-v", "--vhost", type=str, default=None)
@click.option("-C", "--confirmation-factor", type=int, default=1)
@click.option("--concurrency", type=int, default=0)
@click.option("--har-output-dir", default=None)
@click.argument("target_host")
def main(*, target_host, cookie_file, json_output, max_retry_count, plugin_settings, proxy, user_agent, vhost,
         depth_limit, directories_only, files_only, plugins_only, recursive, allow_download, confirmation_factor,
         concurrency, har_output_dir):

    output_manager = textutils.init_log(json_output)
    output_manager.output_header()

    # Ensure the host is of the right format and set it in config
    parsed_url = urlparse(target_host)
    if not parsed_url.scheme:
        parsed_url = urlparse("http://%s" % target_host)

    if not parsed_url:
        output_manager.output_error("Invald URL provided.")
        return

    # Set conf values
    conf.target_host = parsed_url.netloc
    conf.base_url = "%s://%s" % (parsed_url.scheme, parsed_url.netloc)

    hammertime = None
    accumulator = ResultAccumulator(output_manager=output_manager)

    output_manager.output_info('Starting Discovery on ' + conf.base_url)

    conf.allow_download = allow_download
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
        loop = custom_event_loop()
        hammertime = loop.run_until_complete(
            configure_hammertime(cookies=conf.cookies, proxy=conf.proxy_url, retry_count=max_retry_count,
                                 user_agent=conf.user_agent, vhost=conf.forge_vhost,
                                 confirmation_factor=confirmation_factor,
                                 concurrency=concurrency,
                                 har_output_dir=har_output_dir))
        t = loop.create_task(stat_on_input(hammertime))
        loop.run_until_complete(scan(hammertime, accumulator=accumulator,
                                     cookies=conf.cookies, directories_only=directories_only,
                                     files_only=files_only, plugins_only=plugins_only, depth_limit=depth_limit,
                                     recursive=recursive))
        t.cancel()
        output_manager.output_info('Scan completed')

    except (KeyboardInterrupt, asyncio.CancelledError):
        output_manager.output_error('Keyboard Interrupt Received')
    except (OfflineHostException, StopRequest):
        output_manager.output_error("Target host seems to be offline.")
    except ImportError as e:
        output_manager.output_error("Additional module is required for the requested options: %s" % e)
    finally:
        if hammertime is not None:
            textutils.output_info(format_stats(hammertime.stats))

        output_manager.flush()


async def stat_on_input(hammertime):
    import sys
    from datetime import datetime, timedelta

    if sys.stdin is None or not sys.stdin.readable() or not sys.stdin.isatty():
        return

    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    reader_protocol = asyncio.StreamReaderProtocol(reader)

    await loop.connect_read_pipe(lambda: reader_protocol, sys.stdin)

    expiry = datetime.now()
    while True:
        await reader.readline()

        # Throttle stats printing
        if expiry < datetime.now():
            textutils.output_info(format_stats(hammertime.stats))
            expiry = datetime.now() + timedelta(seconds=2)

        if sys.stdin.seekable():
            sys.stdin.seek(-1, sys.SEEK_END)


if __name__ == "__main__":
    main()
