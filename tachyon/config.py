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
from hammertime.rules import DetectSoft404, RejectStatusCode, DynamicTimeout, RejectCatchAllRedirect, FollowRedirects, \
    SetHeader, DeadHostDetection, FilterRequestFromURL, DetectBehaviorChange, IgnoreLargeBody, \
    RejectSoft404

from tachyon import conf
from tachyon.heuristics import RejectIgnoredQuery, LogBehaviorChange, MatchString, RedirectLimiter

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
    hammertime = HammerTime(loop=loop, request_engine=engine, retry_count=retry_count, proxy=proxy)
    setup_hammertime_heuristics(hammertime, **kwargs)
    return hammertime


def setup_hammertime_heuristics(hammertime, *, user_agent=default_user_agent, vhost=None):
    #  TODO Make sure rejecting 404 does not conflict with tomcat fake 404 detection.
    global heuristics_with_child
    detect_soft_404 = DetectSoft404(distance_threshold=6)
    follow_redirects = FollowRedirects()
    heuristics_with_child = [RejectCatchAllRedirect(), follow_redirects,
                             RejectIgnoredQuery()]
    hosts = (vhost, conf.target_host) if vhost is not None else conf.target_host
    global_heuristics = [DynamicTimeout(1.0, 5),
                         RedirectLimiter(),
                         FilterRequestFromURL(allowed_urls=hosts),
                         IgnoreLargeBody(initial_limit=initial_limit)]
    heuristics = [RejectStatusCode({404, 502}),
                  detect_soft_404, RejectSoft404(),
                  MatchString(),
                  DeadHostDetection(threshold=200),
                  DetectBehaviorChange(buffer_size=100), LogBehaviorChange()]
    hammertime.heuristics.add_multiple(global_heuristics)
    hammertime.heuristics.add_multiple(heuristics)
    hammertime.heuristics.add_multiple(heuristics_with_child)
    for heuristic in heuristics_with_child:
        heuristic.child_heuristics.add_multiple(global_heuristics)

    detect_soft_404.child_heuristics.add(follow_redirects)

    add_http_header(hammertime, "User-Agent", user_agent)
    add_http_header(hammertime, "Host", vhost if vhost is not None else conf.target_host)


def add_http_header(hammertime, header_name, header_value):
    set_header = SetHeader(header_name, header_value)
    hammertime.heuristics.add(set_header)
    for heuristic in heuristics_with_child:
        heuristic.child_heuristics.add(set_header)


def set_cookies(hammertime, cookies):
    add_http_header(hammertime, "Cookie", cookies)
