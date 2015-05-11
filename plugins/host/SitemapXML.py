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

import re
from core import conf, textutils, database
from core.fetcher import Fetcher
try:
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urljoin

def add_path(path):
    current_template = conf.path_template.copy()
    current_template['description'] = 'Found in sitemap.xml'
    current_template['is_file'] = False
    current_template['url'] = '/' + path
    database.paths.append(current_template)

def add_file(filename):
    """ Add file to database """
    current_template = conf.path_template.copy()
    current_template['description'] = 'Found in sitemap.xml'
    current_template['url'] = filename
    database.files.append(current_template)

def execute():
    """ Fetch sitemap.xml and add each entry as a target """

    current_template = dict(conf.path_template)
    current_template['description'] = 'sitemap.xml entry'

    target_url = urljoin(conf.target_base_path, "/sitemap.xml")
    fetcher = Fetcher()
    response_code, content, headers = fetcher.fetch_url(target_url,
                                                        conf.user_agent,
                                                        conf.fetch_timeout_secs,
                                                        limit_len=False,
                                                        add_headers={}
                                                        )

    if response_code is 200 or response_code is 302 and content:

        regexp = re.compile(b'(?im).*<url>\s*<loc>(.*)</loc>\s*</url>.*')
        matches = re.findall(regexp, content)

        textutils.output_debug("SitemapXML plugin")

        added = 0
        for match in matches:
            new_path = match.decode().split(conf.target_host)[1]

            # Remove trailing /
            if new_path.endswith('/'):
                new_path = new_path[:-1]   

            add_path(new_path)
            add_file(new_path)

            textutils.output_debug(" - Added: %s from /sitemap.xml" % new_path)

            added += 1

        if added > 0:
            textutils.output_info(' - SitemapXML Plugin: added %d base paths '
                                  'using /sitemap.xml' % added)
        else :
            textutils.output_info(' - SitemapXML Plugin: no usable entries '
                                  'in /sitemap.xml')
               
    else:
        textutils.output_info(' - SitemapXML Plugin: /sitemap.xml not found on '
                              'target site')

