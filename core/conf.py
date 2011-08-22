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

# Internal config and consts
version = '0.4'
expected_path_responses = [200, 302, 401]
crc_sample_len = 2048

# Templates, used by plugins
path_template = {'url': '', 'timeout_count': 0, 'description': ''}

# Values used to generate file list (maybe this sould be configurable)
file_suffixes = ['.sql', '.bak', '.old', '_old', '-old', 'oldold', '.dmp', '.dump', '.zip',
                '.tar.gz', '.tar.bz2', '.tar', '_bak', '-bak', '~', '.swp', '.conf', '.ini',
                '.txt', '.php.old', '.log', '.pwd', '.sql.old', '0', '1', '2', '.new',
                '.xml', '_log', '-log', '.csv']

# User config
debug = False
use_head = False
search_files = True
fetch_timeout_secs = 3
max_timeout_count = 5
thread_count = 25
target_host = ''
use_tor = False
content_type_blacklist = True
raw_output = False
user_agent = 'Mozilla/5.0 (Windows; U; MSIE 9.0; WIndows NT 9.0; en-US)' # maximum compatibility


# Templates, used by plugins
path_template = {'url': '', 'expected_response': [200, 302, 401], 'timeout_count': 0, 'description': ''}
  
