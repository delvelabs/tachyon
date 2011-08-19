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
from core import conf

def execute():
    """ This plugin process the hostname to generate host and filenames relatives to it """
    target = conf.target_host
    
    # Remove char to figure out the human-likely expressed domain name
    # www.test.ca = testca, test
    # host.host.host.com = hosthosthost.com. host.com hostcom, host
    # /host.ext
    
        
    
    # We don't test for directory like domain.dom/domain since "cp * ./sitename" is unlikely to happen (questionable)    
        
    