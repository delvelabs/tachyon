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


from hammertime import HammerTime
from hammertime.rules import DetectSoft404, RejectStatusCode, DynamicTimeout, RejectCatchAllRedirect, FollowRedirects, \
    SetHeader, DeadHostDetection, FilterRequestFromURL, DetectBehaviorChange, IgnoreLargeBody
from aiohttp import ClientSession, TCPConnector
from aiohttp.helpers import DummyCookieJar
from hammertime.engine import AioHttpEngine
from hammertime.config import custom_event_loop

from tachyon.core.heuristics import RejectIgnoredQuery, LogBehaviorChange, MatchString
from tachyon.core import conf


heuristics_with_child = []


def configure_hammertime():
    loop = custom_event_loop()
    engine = AioHttpEngine(loop=loop, verify_ssl=False, proxy=conf.proxy_url)
    if conf.cookies is not None:
        engine.session.close()
        connector = TCPConnector(loop=loop, verify_ssl=False)
        engine.session = ClientSession(loop=loop, connector=connector, cookie_jar=DummyCookieJar(loop=loop))
    hammertime = HammerTime(loop=loop, request_engine=engine, retry_count=3, proxy=conf.proxy_url)
    setup_hammertime_heuristics(hammertime)
    return hammertime


def setup_hammertime_heuristics(hammertime):
    #  TODO Make sure rejecting 404 does not conflict with tomcat fake 404 detection.
    global heuristics_with_child
    heuristics_with_child = [DetectSoft404(distance_threshold=6), FollowRedirects(), RejectCatchAllRedirect(),
                             RejectIgnoredQuery()]
    global_heuristics = [DeadHostDetection(), DynamicTimeout(0.5, 5), DetectBehaviorChange(), LogBehaviorChange(),
                         FilterRequestFromURL(allowed_urls=conf.target_host),
                         IgnoreLargeBody(initial_limit=conf.file_sample_len)]
    heuristics = [RejectStatusCode({404, 502}), MatchString()]
    hammertime.heuristics.add_multiple(heuristics)
    hammertime.heuristics.add_multiple(heuristics_with_child)
    hammertime.heuristics.add_multiple(global_heuristics)
    for heuristic in heuristics_with_child:
        heuristic.child_heuristics.add_multiple(global_heuristics)
    add_http_header(hammertime, "User-Agent", conf.user_agent)
    add_http_header(hammertime, "Host", conf.target_host)


def add_http_header(hammertime, header_name, header_value):
    set_header = SetHeader(header_name, header_value)
    hammertime.heuristics.add(set_header)
    for heuristic in heuristics_with_child:
        heuristic.child_heuristics.add(set_header)


def set_cookies(hammertime, cookies):
    add_http_header(hammertime, "Cookie", cookies)
