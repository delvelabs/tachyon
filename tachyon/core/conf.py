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

from collections import defaultdict

# Internal config and consts
name = "delvelabs/tachyon"

# Templates, used by plugins
path_template = {'url': '', 'timeout_count': 0, 'description': ''}

# User config
target_host = ''
target_base_path = ''
target_port = 80
base_url = ''
is_ssl = False
scheme = ''
search_files = True
fetch_timeout_secs = 2
max_timeout_secs = 15
test_plugin = None
allow_download = False
eval_output = False

plugin_settings = defaultdict(list)
