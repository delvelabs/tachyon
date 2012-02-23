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
from core import database
from core import conf

class Fetcher(object):
    def fetch_url(self, url, user_agent, timeout, limit_len=True, add_headers=dict()):
        """ Fetch a given url, with a given user_agent and timeout"""
        try:
            if not add_headers.get('User-Agent'):
                add_headers['User-Agent'] = user_agent
            if not add_headers.get('Connection'):
                add_headers['Connection'] = 'Keep-Alive'
            if not add_headers.get('Host'):
                add_headers['Host'] = conf.target_host

            # Session cookie
            if database.session_cookie:
                add_headers['Cookie'] = database.session_cookie

            # Limit request len on binary types
            if limit_len:
                content_range = 'bytes=0-' + str(conf.file_sample_len-1)
                add_headers['Range'] = content_range

            response = database.connection_pool.request('GET', url, headers=add_headers, retries=0, redirect=False,
                                                        release_conn=True, assert_same_host=False, timeout=timeout)

            content = response.data
            code = response.status
            headers = response.headers
        except Exception:
            code = 0
            content = ''
            headers = dict()

        return code, content, headers
        
        