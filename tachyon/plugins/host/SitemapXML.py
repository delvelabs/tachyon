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
#

import re
from urllib.parse import urljoin
from urllib.parse import urlparse

from hammertime.ruleset import StopRequest, RejectRequest

from tachyon import conf, textutils, database


def add_path(path):
    current_template = conf.path_template.copy()
    current_template['description'] = 'Found in sitemap.xml'
    current_template['is_file'] = False
    current_template['url'] = '/' + path
    if current_template not in database.paths:
        database.paths.append(current_template)
        return True


def add_file(filename):
    """ Add file to database """
    current_template = conf.path_template.copy()
    current_template['description'] = 'Found in sitemap.xml'
    current_template['url'] = filename
    if current_template not in database.files:
        database.files.append(current_template)
        return True


async def execute(hammertime):
    """ Fetch sitemap.xml and add each entry as a target """

    current_template = dict(conf.path_template)
    current_template['description'] = 'sitemap.xml entry'

    target_url = urljoin(conf.base_url, "/sitemap.xml")

    try:
        entry = await hammertime.request(target_url)

        regexp = re.compile('(?im).*<url>\s*<loc>(.*)</loc>\s*</url>.*')
        matches = re.findall(regexp, entry.response.content)

        added = 0
        for match in matches:
            if not isinstance(match, str):
                match = match.decode('utf-8', 'ignore')
            parsed = urlparse(match)
            if parsed.path:
                new_path = parsed.path
            else:
                continue

            # Remove trailing /
            if new_path.endswith('/'):
                new_path = new_path[:-1]

            if add_path(new_path):
                added += 1

        if added > 0:
            textutils.output_info(' - SitemapXML Plugin: added %d base paths '
                                  'using /sitemap.xml' % added)
        else:
            textutils.output_info(' - SitemapXML Plugin: no usable entries '
                                  'in /sitemap.xml')
    except (StopRequest, RejectRequest):
        textutils.output_info(' - SitemapXML Plugin: /sitemap.xml not found on '
                              'target site')
