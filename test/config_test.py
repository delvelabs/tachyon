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

from aiohttp import TCPConnector
from aiohttp.cookiejar import DummyCookieJar
from aiohttp.test_utils import make_mocked_coro
from fixtures import async
from hammertime.core import HammerTime
from hammertime.rules import RejectCatchAllRedirect, FollowRedirects, FilterRequestFromURL

from tachyon import conf, config


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
        user_agent = "My-user-agent"

        with patch("tachyon.config.add_http_header") as add_http_header:
            await config.configure_hammertime(user_agent=user_agent)

        add_http_header.assert_any_call(ANY, "User-Agent", user_agent)

    @async()
    async def test_configure_hammertime_add_host_header_to_request_header(self):
        conf.target_host = "example.com"

        with patch("tachyon.config.add_http_header") as add_http_header:
            await config.configure_hammertime()

        add_http_header.assert_any_call(ANY, "Host", conf.target_host)

    @async()
    async def test_configure_hammertime_use_user_supplied_vhost_for_host_header(self):
        conf.target_host = "example.com"
        forge_vhost = "vhost.example.com"

        with patch("tachyon.config.add_http_header") as add_http_header:
            await config.configure_hammertime(vhost=forge_vhost)

        add_http_header.assert_any_call(ANY, "Host", forge_vhost)

    @async()
    async def test_configure_hammertime_allow_requests_to_user_supplied_vhost(self):
        conf.target_host = "example.com"
        forge_vhost = "vhost.example.com"

        with patch("tachyon.config.FilterRequestFromURL", MagicMock(return_value=FilterRequestFromURL)) as url_filter:
            await config.configure_hammertime(vhost=forge_vhost)

            _, kwargs = url_filter.call_args
            self.assertEqual(kwargs["allowed_urls"], ("vhost.example.com", "example.com"))

    @async()
    async def test_configure_hammertime_create_aiohttp_engine_for_hammertime(self, loop):
        engine = MagicMock()
        engine.session.close = make_mocked_coro()
        EngineFactory = MagicMock(return_value=engine)
        with patch("tachyon.config.AioHttpEngine", EngineFactory):
            hammertime = await config.configure_hammertime(proxy="my-proxy")

            EngineFactory.assert_called_once_with(loop=loop, verify_ssl=False, proxy="my-proxy")
            self.assertEqual(hammertime.request_engine.request_engine, engine)

    @async()
    async def test_configure_hammertime_create_client_session_with_dummy_cookie_jar_if_user_supply_cookies(self):
        cookies = "not none"
        with patch("tachyon.config.ClientSession") as SessionFactory:
            await config.configure_hammertime(cookies=cookies)

            _, kwargs = SessionFactory.call_args
            self.assertTrue(isinstance(kwargs["cookie_jar"], DummyCookieJar))

    @async()
    async def test_configure_hammertime_configure_aiohttp_to_resolve_host_only_once(self, loop):
        with patch("tachyon.config.TCPConnector", MagicMock(return_value=TCPConnector(loop=loop))) as \
                ConnectorFactory:
            await config.configure_hammertime()

            _, kwargs = ConnectorFactory.call_args
            self.assertTrue(kwargs["use_dns_cache"])
            self.assertIsNone(kwargs["ttl_dns_cache"])
