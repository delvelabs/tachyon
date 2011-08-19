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

import Queue

""" Path list is used to hold loaded path from disk """
paths = list()

""" File list is used to hold loaded filenames from disk """
files = list()

""" Valid path is used to store the path that were found before merging with filenames """
valid_paths = list()

""" Fetch List contains all the url that have to be fetched by the workers """
fetch_queue = Queue.Queue(maxsize=0)

""" output contains the scan results """
output_queue = Queue.Queue(maxsize=0)

""" Contains the initial 404 hash value for the domain root """
root_404_crc = ''