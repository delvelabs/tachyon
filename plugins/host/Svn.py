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

from core import conf, textutils, database, dbutils
from core.fetcher import Fetcher
from urlparse import urljoin
from xml.etree import ElementTree


def parse_svn_entries(url):
    description_file = 'SVN entries file at'
    description_dir = "SVN entries Dir at"
    target_url = url + "/.svn/entries"
    fetcher = Fetcher()
    response_code, content, headers = fetcher.fetch_url(target_url, conf.user_agent, conf.fetch_timeout_secs, limit_len=False)

    if response_code is 200 or response_code is 302 and content:
        tokens = content.split('\n')
        if 'dir' in tokens:
            for pos, token in enumerate(tokens):
                if token == 'dir':
                    # Fetch more entries recursively
                    if tokens[pos-1] != '':
                        textutils.output_found(description_dir + ' at: ' + url + '/' + tokens[pos-1])
                        parse_svn_entries(url + "/" + tokens[pos-1])
                elif token == 'file':
                    textutils.output_found(description_file + ' at: ' + url + '/' + tokens[pos-1])


def execute():
    """ Fetch /.svn/entries and parse for target paths """

    textutils.output_info(' - Svn Plugin: Searching for /.svn/entries')
    target_url = conf.target_base_path + "/.svn/entries"

    fetcher = Fetcher()
    response_code, content, headers = fetcher.fetch_url(target_url, conf.user_agent, conf.fetch_timeout_secs, limit_len=False)
    if response_code is 200 or response_code is 302:
        textutils.output_info(' - Svn Plugin: /.svn/entries found! crawling... (use svn-extractor to download)')
        parse_svn_entries(conf.target_base_path)
    else:
        textutils.output_info(' - Svn Plugin: no /.svn/entries found')

