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

from core import conf, textutils, database
from core.fetcher import Fetcher
from urlparse import urljoin
from xml.etree import ElementTree

def execute():
    """ Fetch /.svn/entries and parse for target paths """
    current_template = dict(conf.path_template)
    current_template['description'] = '/.svn/entries found directory'

    target_url = urljoin(conf.target_base_path, "/.svn/entries")
    fetcher = Fetcher()
    response_code, content, headers = fetcher.fetch_url(target_url, conf.user_agent, conf.fetch_timeout_secs, limit_len=False)

    if response_code is 200 or response_code is 302 and content:
        added = 0
        try:
            tree = ElementTree.fromstring(content)
            entry_tags = tree.iter()
            if entry_tags:
                for entry in entry_tags:
                    kind = entry.attrib.get("kind")
                    if kind and kind == "dir":
                        current_template = dict(current_template)
                        current_template['url'] = '/' + entry.attrib["name"]
                        database.paths.append(current_template)
                        added += 1

        except Exception:
            textutils.output_info(' - Svn Plugin: no usable entries in /.svn/entries')
        else:
            if added > 0:
                textutils.output_info(' - Svn Plugin: added ' + str(added) + ' base paths using /.svn/entries')
            else :
                textutils.output_info(' - Svn Plugin: no usable entries in /.svn/entries')
    else:
        textutils.output_info(' - Svn Plugin: no /.svn/entries found')

