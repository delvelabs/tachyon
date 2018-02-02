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

import random
import socket

from .import textutils, database

def _get_random_ip_from_cache(cache_info):
    """ Get a random ip from the caches entries """
    random_entry = cache_info[random.randint(0, len(cache_info) - 1)]
    host_port = random_entry[4]
    return host_port[0]

def get_host_ip(host, port):
    """ Fetch the resolved ip addresses from the cache and return a random address if load-balanced """
    resolved = database.dns_cache.get(host)
    if not resolved:
        textutils.output_debug("Host entry not found in cache for host:" + str(host) + ", resolving")
        resolved = socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM)
        database.dns_cache[host] = resolved

    return _get_random_ip_from_cache(resolved), port
