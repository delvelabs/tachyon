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

import os
import sqlite3
from ...core import conf, textutils, database, dbutils
from ...core.fetcher import Fetcher
from xml.etree import ElementTree

base_headers = dict()

def save_file(path, content):
    output = "output/" + conf.target_host + path

    if not os.path.exists(output[:output.rfind('/')]):
        os.makedirs(output[:output.rfind('/')])

    with open(output, "wb") as outfile:
        if isinstance(content, str):
            outfile.write(content.encode('utf-8'))
        else:
            outfile.write(content)

# Fixme
#def parse_svn_17_db(filename):
#    conn = sqlite3.connect(filename)
#    files = conn.execute('select local_relpath, ".svn/pristine/" || substr(checksum,7,2) || "/" || substr(checksum,7) || ".svn-base" as alpha from NODES;')
#    #for entries in files:
#    #    if
#    pass

def parse_svn_entries(url):
    description_file = 'SVN entries file at'
    description_dir = "SVN entries Dir at"
    target_url = url + "/.svn/entries"
    fetcher = Fetcher()

    response_code, content, headers = fetcher.fetch_url(target_url, conf.user_agent, conf.fetch_timeout_secs, limit_len=False, add_headers=base_headers)
    if not isinstance(content, str):
        content = content.decode('utf-8', 'ignore')

    if response_code in conf.expected_file_responses and content:
        tokens = content.split('\n')
        if 'dir' in tokens:
            for pos, token in enumerate(tokens):
                if token == 'dir':
                    # Fetch more entries recursively
                    if tokens[pos-1] != '':
                        textutils.output_debug(' - Svn Plugin: Found dir: ' + url + '/' + tokens[pos-1])

                        if conf.allow_download:
                            textutils.output_info(' - Svn Plugin: Downloading: ' + url + '/' + tokens[pos-1] + '\r')
                        else:
                            textutils.output_found(description_dir + ' at: ' + url + '/' + tokens[pos-1])

                        # Parse next
                        parse_svn_entries(url + "/" + tokens[pos-1])

                elif token == 'file':
                    textutils.output_debug(' - Svn Plugin: Found file: ' + url + '/' + tokens[pos-1])
                    if conf.allow_download:
                        textutils.output_info(' - Svn Plugin: Downloading: ' + url + '/' + tokens[pos-1] + '\r')
                        # Fetch text-base file
                        path = url + "/.svn/text-base" + '/' + tokens[pos-1] + ".svn-base"
                        fetcher = Fetcher()
                        response_code, content, headers = fetcher.fetch_url(path, conf.user_agent,
                                                                            conf.fetch_timeout_secs, limit_len=False)
                        save_file(url + '/' + tokens[pos-1], content)
                    else:
                        textutils.output_found(description_file + ' at: ' + url + '/' + tokens[pos-1])


def execute():
    """ Fetch /.svn/entries and parse for target paths """

    textutils.output_info(' - Svn Plugin: Searching for /.svn/entries')
    target_url = conf.target_base_path + "/.svn/entries"

    fetcher = Fetcher()
    response_code, content, headers = fetcher.fetch_url(target_url, conf.user_agent, conf.fetch_timeout_secs, limit_len=False)
    svn_legacy = True

    if not isinstance(content, str):
        content = content.decode('utf-8', 'ignore')

    if response_code in conf.expected_file_responses and content:

        if conf.allow_download:
            textutils.output_info(' - Svn Plugin: /.svn/entries found! crawling... (will download files to output/)')
        else:
            textutils.output_info(' - Svn Plugin: /.svn/entries found! crawling... (use -a to download files instead of printing)')
       
        # test for version 1.7+
        target_url = conf.target_base_path + "/.svn/wc.db"
        fetcher = Fetcher()
        response_code, content, headers = fetcher.fetch_url(target_url, conf.user_agent, conf.fetch_timeout_secs, limit_len=False)

        #if response_code in conf.expected_file_responses and content:
        #    textutils.output_info(' - Svn Plugin: SVN 1.7+ detected, parsing wc.db')
        #    svn_legacy = False
        #    save_file(conf.target_base_path + '/wc.db', content)

        # Process index
        if svn_legacy:
            # parse entries
            parse_svn_entries(conf.target_base_path)
        #else:
          #  parse_svn_17_db(conf.target_base_path + '/wc.db')

        # Clean up display
        if conf.allow_download:
            textutils.output_info('')
    else:
        textutils.output_info(' - Svn Plugin: no /.svn/entries found')

