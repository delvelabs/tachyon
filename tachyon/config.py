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


from aiohttp import ClientSession, TCPConnector
from aiohttp.cookiejar import DummyCookieJar
from hammertime import HammerTime
from hammertime.config import custom_event_loop
from hammertime.engine import AioHttpEngine
from hammertime.kb import KnowledgeBase
from hammertime.ruleset import StopRequest
from hammertime.rules import DetectSoft404, RejectStatusCode, DynamicTimeout, RejectCatchAllRedirect, FollowRedirects, \
    SetHeader, DeadHostDetection, FilterRequestFromURL, DetectBehaviorChange, IgnoreLargeBody

from tachyon import conf
from tachyon.heuristics import RejectIgnoredQuery, LogBehaviorChange, MatchString, RedirectLimiter, StripTag
from tachyon.filefetcher import ValidateEntry

heuristics_with_child = []
initial_limit = 5120
default_user_agent = 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) ' \
                     'Chrome/41.0.2228.0 Safari/537.36'


async def configure_hammertime(proxy=None, retry_count=3, cookies=None, **kwargs):
    loop = custom_event_loop()
    engine = AioHttpEngine(loop=loop, verify_ssl=False, proxy=proxy)
    await engine.session.close()
    connector = TCPConnector(loop=loop, verify_ssl=False, use_dns_cache=True, ttl_dns_cache=None)
    if cookies is not None:
        engine.session = ClientSession(loop=loop, connector=connector, cookie_jar=DummyCookieJar(loop=loop))
    else:
        engine.session = ClientSession(loop=loop, connector=connector)
    kb = KnowledgeBase()
    hammertime = HammerTime(loop=loop, request_engine=engine, retry_count=retry_count, proxy=proxy, kb=kb)
    setup_hammertime_heuristics(hammertime, **kwargs)
    hammertime.collect_successful_requests()
    hammertime.kb = kb
    return hammertime


def setup_hammertime_heuristics(hammertime, *, user_agent=default_user_agent, vhost=None, confirmation_factor=1):
    #  TODO Make sure rejecting 404 does not conflict with tomcat fake 404 detection.
    global heuristics_with_child
    dead_host_detection = DeadHostDetection(threshold=200)
    detect_soft_404 = DetectSoft404(distance_threshold=6, confirmation_factor=confirmation_factor)
    follow_redirects = FollowRedirects()
    heuristics_with_child = [RejectCatchAllRedirect(), follow_redirects,
                             RejectIgnoredQuery()]
    hosts = (vhost, conf.target_host) if vhost is not None else conf.target_host

    init_heuristics = [SetHeader("User-Agent", user_agent),
                       SetHeader("Host", vhost if vhost is not None else conf.target_host),
                       dead_host_detection,
                       RejectStatusCode({503, 508}, exception_class=StopRequest),
                       StripTag('input'), StripTag('script')]

    global_heuristics = [RejectStatusCode({404, 406, 502}),
                         DynamicTimeout(1.0, 5),
                         RedirectLimiter(),
                         FilterRequestFromURL(allowed_urls=hosts),
                         IgnoreLargeBody(initial_limit=initial_limit)]

    # Dead host detection must be first to make sure there is no skipped after_headers
    hammertime.heuristics.add_multiple(init_heuristics)

    # General
    hammertime.heuristics.add_multiple(global_heuristics)
    hammertime.heuristics.add_multiple(heuristics_with_child)
    hammertime.heuristics.add_multiple([
        detect_soft_404,
        MatchString(),
        ValidateEntry(),
        DetectBehaviorChange(buffer_size=100),
        LogBehaviorChange(),
        ValidateEntry(),
    ])
    detect_soft_404.child_heuristics.add_multiple(init_heuristics)
    detect_soft_404.child_heuristics.add_multiple(heuristics_with_child)

    for heuristic in heuristics_with_child:
        heuristic.child_heuristics.add_multiple(init_heuristics)
        heuristic.child_heuristics.add_multiple(global_heuristics)


def add_http_header(hammertime, header_name, header_value):
    set_header = SetHeader(header_name, header_value)
    hammertime.heuristics.add(set_header)
    for heuristic in heuristics_with_child:
        heuristic.child_heuristics.add(set_header)


def set_cookies(hammertime, cookies):
    add_http_header(hammertime, "Cookie", cookies)
