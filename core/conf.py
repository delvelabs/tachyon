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
version = '2.0.0-beta6'
expected_path_responses = [200, 206, 401, 403]
expected_file_responses = [200, 206]
timeout_codes = [0, 500, 502, 503]
redirect_codes = [301, 302, 303, 307]
file_sample_len = 200

# Templates, used by plugins
path_template = {'url': '', 'timeout_count': 0, 'description': ''}

# Extensions used by crafted 404 sampling
crafted_404_extensions = ['', '.php', '.jsp', '.asp', '.html']

# Values used to generate file list (maybe this sould be configurable)
file_suffixes = ['', '.sql', '.bak', '-bak', '.old', '-old', '.dmp', '.dump', '.zip', '.rar', '.7z',
                '.tar.gz', '.tar.bz2', '.tar', '.tgz', '-bak', '~', '.conf.old','.conf',
                '.conf.orig', '.conf.bak', '.cnf', '.ini', '.inc', '.inc.old', '.inc.orig', '.log', '.txt', '_log',
                '.php.old', '.php.inc', '.php.orig', '.sql.old', '.sql.bak', '0', '1', '2', '.xml',
                '.csv']

# User config
target_host = ''
target_base_path = ''
is_ssl = False
forge_vhost='' 

debug = False
search_files = True
recursive = False
fetch_timeout_secs = 3
max_timeout_count = 10
thread_count = 150
use_tor = False
raw_output = False
user_agent = 'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; Trident/6.0)' # maximum compatibility
files_only = False
directories_only = False
throttle_increment = 0.5
max_throttle = 10.0 # in seconds
recursive_depth_limit=2
test_plugin = None



# Templates, used by plugins
path_template = {'url': '', 'timeout_count': 0, 'description': ''}
  
