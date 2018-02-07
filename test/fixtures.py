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

import asyncio
from functools import wraps
from aiohttp.test_utils import loop_context
from hammertime.http import StaticResponse
from urllib.parse import urlparse

from easyinject import Injector


def async():
    def setup(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            with loop_context() as loop:
                injector = Injector(loop=loop,
                                    fake_future=lambda: fake_future)
                asyncio.get_child_watcher().attach_loop(loop)
                asyncio.set_event_loop(loop)
                loop.run_until_complete(injector.call(f, *args, **kwargs))
        return wrapper
    return setup


def fake_future(result, loop):
    f = asyncio.Future(loop=loop)
    f.set_result(result)
    return f


def create_json_data(url_list, **kwargs):
    data_list = []
    for url in url_list:
        desc = "description of %s" % url.strip("/")
        data = {"url": url, "description": desc, "timeout_count": 0, "severity": "warning"}
        data.update(**kwargs)
        data_list.append(data)
    return data_list


class FakeHammerTimeEngine:

    async def perform(self, entry, heuristics):
        await heuristics.before_request(entry)
        entry.response = StaticResponse(200, headers={})
        await heuristics.after_headers(entry)
        entry.response.set_content(b"data", at_eof=False)
        await heuristics.after_response(entry)
        return entry


class SetResponseCode:

    def __init__(self, response_code):
        self.response_code = response_code

    async def after_headers(self, entry):
        entry.response.code = self.response_code


class SetResponseContent:

    def __init__(self, raw):
        self.content = raw

    async def after_response(self, entry):
        entry.response.content = self.content


class RaiseForPaths:

    def __init__(self, invalid_paths, exception):
        self.invalid_paths = invalid_paths
        self.exception = exception

    async def before_request(self, entry):
        path = urlparse(entry.request.url).path
        if path in self.invalid_paths:
            raise self.exception
