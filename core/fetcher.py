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
from _socket import timeout
from urllib2 import URLError, HTTPError, urlopen, Request, ProxyHandler, build_opener, install_opener
from httplib import BadStatusLine
from core import conf, utils


class Fetcher(object):
    def read_content(self, response, limit_len=True):
        """ Reads the content from the response and build a string with it """
        if limit_len:
            content = response.read(conf.crc_sample_len)
        else:
            content = ''
            while True:
                try:
                    tmp = response.read(1024)
                    if tmp == '':
                        break
                    else:
                        content = content + tmp
                except timeout:
                        raise timeout

        return content    

    def fetch_url(self, url, user_agent, timeout, limit_len=True):
        """ Fetch a given url, with a given user_agent and timeout"""
        try:
            if conf.use_tor:
                proxy_support = ProxyHandler({'http': 'http://127.0.0.1:8118/'})
                opener = build_opener(proxy_support)
                install_opener(opener)
            else:
                opener = build_opener()
                
            opener.addheaders = [('User-Agent', user_agent)]    
            response = opener.open(url, timeout=timeout)
            
            content = self.read_content(response, limit_len)
            code = response.code
            headers = dict(response.headers)
            response.close()
        except HTTPError as httpe:
            code = httpe.code
            content = ''
            headers = dict(httpe.headers)
        except (URLError, BadStatusLine, timeout):
            code = 0
            content = ''
            headers = dict()
            
        return code, content, headers
