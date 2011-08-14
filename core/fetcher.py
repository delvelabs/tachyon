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

from urllib2 import URLError, HTTPError, urlopen, Request

class Fetcher(object):
    def fetch_url(self, url, method, user_agent, fetch_content, timeout):
        try:
            request = Request(url)
            request.addheaders = [('User-agent', user_agent)]
            request.get_method = lambda : method
            response = urlopen(request, timeout=timeout)
            content = ''

            if fetch_content:
                while True:
                    tmp = response.read(1024)
                    if tmp == '':
                        break
                    else:
                        content = content + tmp
            else:
                content = None

            code = response.code
            headers = dict(response.headers)
            response.close()
        except HTTPError as httpe:
            code = httpe.code
            content = None
            headers = dict(httpe.headers)
        except URLError:
            code = 0
            content = None
            headers = dict()

        return code, content, headers
