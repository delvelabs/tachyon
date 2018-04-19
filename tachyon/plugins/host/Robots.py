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

from hammertime.ruleset import StopRequest, RejectRequest

from tachyon import conf, textutils, database


async def execute(hammertime):
    """ Fetch /robots.txt and add the disallowed paths as target """
    current_template = dict(conf.path_template)
    current_template['description'] = 'Robots.txt entry'

    target_url = urljoin(conf.base_url, "/robots.txt")

    try:
        entry = await hammertime.request(target_url)
        matches = re.findall(r'Disallow:\s*/[a-zA-Z0-9-/\r]+\n', entry.response.content)

        added = 0
        for match in matches:
            # Filter out some characters
            match = filter(lambda c: c not in ' *?.\n\r\t', match)

            if match:
                match = ''.join(match)

            # Split on ':'
            splitted = match.split(':')
            if splitted[1]:
                target_path = splitted[1]

                # Remove trailing /
                if target_path.endswith('/'):
                    target_path = target_path[:-1]

                current_template = current_template.copy()
                current_template['url'] = target_path
                database.paths.append(current_template)
                added += 1

        if added > 0:
            textutils.output_info(' - Robots Plugin: added ' + str(added) + ' base paths using /robots.txt')
        else:
            textutils.output_info(' - Robots Plugin: no usable entries in /robots.txt')
    except (StopRequest, RejectRequest):
        textutils.output_info(' - Robots Plugin: /robots.txt not found on target site')
