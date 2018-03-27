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


from unittest import TestCase
from unittest.mock import MagicMock, patch, ANY
from aiohttp.helpers import DummyCookieJar
from hammertime.core import HammerTime
from hammertime.rules import RejectCatchAllRedirect, FollowRedirects

from tachyon.core import conf
from tachyon.core import config
from fixtures import fake_future, async, patch_coroutines


class TestConfig(TestCase):

    @async()
    async def test_add_http_headers(self, loop):
        hammertime = HammerTime(loop=loop)
        config.heuristics_with_child = [RejectCatchAllRedirect(), FollowRedirects()]
        hammertime.heuristics.add_multiple(config.heuristics_with_child)
        hammertime.heuristics.add = MagicMock()
        for heuristic in config.heuristics_with_child:
            heuristic.child_heuristics.add = MagicMock()

        config.add_http_header(hammertime, "header", "value")

        set_header = hammertime.heuristics.add.call_args[0][0]
        self.assertEqual(set_header.name, "header")
        self.assertEqual(set_header.value, "value")
        for heuristic_with_child in config.heuristics_with_child:
            set_header = heuristic_with_child.child_heuristics.add.call_args[0][0]
            self.assertEqual(set_header.name, "header")
            self.assertEqual(set_header.value, "value")

    @async()
    async def test_configure_hammertime_add_user_agent_to_request_header(self):
        conf.user_agent = "My-user-agent"

        with patch("tachyon.core.config.add_http_header") as add_http_header:
            config.configure_hammertime()

        add_http_header.assert_any_call(ANY, "User-Agent", conf.user_agent)

    @async()
    async def test_configure_hammertime_add_host_header_to_request_header(self):
        conf.target_host = "example.com"

        with patch("tachyon.core.config.add_http_header") as add_http_header:
            config.configure_hammertime()

        add_http_header.assert_any_call(ANY, "Host", conf.target_host)

    @async()
    async def test_configure_hammertime_create_aiohttp_engine_for_hammertime(self, loop):
        engine = MagicMock()
        conf.proxy_url = "my-proxy"
        EngineFactory = MagicMock(return_value=engine)
        with patch("tachyon.core.config.AioHttpEngine", EngineFactory):
            hammertime = config.configure_hammertime()

            EngineFactory.assert_called_once_with(loop=loop, verify_ssl=False, proxy="my-proxy")
            self.assertEqual(hammertime.request_engine.request_engine, engine)

    @async()
    async def test_configure_hammertime_create_client_session_with_dummy_cookie_jar_if_user_supply_cookies(self):
        conf.proxy_url = "my-proxy"
        conf.cookies = "not none"
        with patch("tachyon.core.config.ClientSession") as SessionFactory:
            config.configure_hammertime()

            _, kwargs = SessionFactory.call_args
            self.assertTrue(isinstance(kwargs["cookie_jar"], DummyCookieJar))
