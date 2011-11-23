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
from core import database, conf, textutils

def decrease_throttle_delay():
    """ If we reach this code, a worker successfully completed a request, we reduce throttling for all threads."""
    if database.throttle_delay > 0:
        database.throttle_delay -= conf.throttle_increment
        if conf.debug:
            textutils.output_debug('Decreasing throttle limit: ' + str(database.throttle_delay))

def increase_throttle_delay():
    """ A worker encountered a timeout, we need to increase throttle time for all threads. """
    if database.throttle_delay < conf.max_throttle:
        database.throttle_delay += conf.throttle_increment
        if conf.debug:
            textutils.output_debug('Increasing throttle limit: ' + str(database.throttle_delay))

def get_throttle():
    """ Throttle anyone who call this with the current throttle delay """
    if database.throttle_delay > 0.0:
        return database.throttle_delay
    else:
        return 0.0

