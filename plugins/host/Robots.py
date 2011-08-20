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
from core import conf, utils, database
from core.fetcher import Fetcher
from urlparse import urljoin

def execute():
    """ Fetch /robots.txt and add the disallowed paths as target """
    current_template = dict(conf.path_template)
    current_template['description'] = 'Robots.txt entry'

    target_url = urljoin(conf.target_host, "/robots.txt")
    fetcher = Fetcher()
    response_code, content, headers = fetcher.fetch_url(target_url, conf.user_agent, conf.fetch_timeout_secs)

    if response_code is 200 or response_code is 302 and content:
        matches = re.findall(r'Disallow:\s*/[a-zA-Z0-9-/\r]+\n', content)
        added = 0
        for match in matches:
            # Filter out some characters
            match = filter(lambda c: c not in ' *?.\n\r', match)
            
            if conf.debug:
                utils.output_debug(match)
                
            # Split on ':'               
            splitted = match.split(':')
            if splitted[1]:
                target_path = splitted[1]
                
                # Remove trailing /
                if target_path.endswith('/'):
                    target_path = target_path[:-1]   

                current_template = dict(current_template)
                current_template['url'] = target_path
                
                if current_template not in database.paths: 
                    database.paths.append(current_template)

                if conf.debug:
                    utils.output_debug(' - Robots Plugin Added: ' + str(target_path) + ' from robots.txt')
                    
                added += 1
                    
        if added > 0:
            utils.output_info(' - Robots Plugin: added ' + str(added) + ' base paths using /robots.txt')
        else :
            utils.output_info(' - Robots Plugin: no usable entries in /robots.txt')
               
    else:
        utils.output_info(' - Robots Plugin: /robots.txt not found on target site')

