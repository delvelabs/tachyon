# Tachyon - Fast Multi-Threaded Web Discovery Tool
# Copyright (c) 2011 Gabriel Tremblay - initnull hat gmail.com
# Copyright (C) 2018-  Delve Labs inc.
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
from tachyon import conf, textutils, database


async def execute(hammertime):
    """ This plugin process the hostname to generate host and filenames relatives to it """
    target = conf.target_host

    # Remove char to figure out the human-likely expressed domain name
    # host.host.host.com = hosthosthost.com. host.com hostcom, host, /host.ext
    # We don't test for domain.dom/domain since "cp * ./sitename" is unlikely to happen (questionable)
    added = 0

    # http://oksala.org -> oksala.org
    target = target.replace('http://', '')
    target = target.replace('https://', '')

    # Remove subpath
    first_slash = target.find('/')
    if first_slash > 0:
        target = target[0:first_slash]

    target = target.replace('/', '')
    new_target = conf.path_template.copy()
    new_target['url'] = target
    new_target['description'] = "HostProcessor generated filename"
    database.files.append(new_target)
    added += 1

    # www.oksala.org -> oksala.org
    target = target.replace('www.', '')
    new_target = conf.path_template.copy()
    new_target['url'] = target
    new_target['description'] = "HostProcessor generated filename"
    database.files.append(new_target)
    added += 1

    # oksala.org -> oksala
    dom_pos = target.rfind('.')
    nodom_target = target[0:dom_pos]
    new_target = conf.path_template.copy()
    new_target['url'] = nodom_target
    new_target['description'] = "HostProcessor generated filename"
    database.files.append(new_target)
    added += 1

    # shortdom (blabla.ok.ok.test.com -> test)
    new_target = conf.path_template.copy()
    dom_pos = target.rfind('.')
    if dom_pos > 0:
        nodom_target = target[0:dom_pos]
        start_pos = nodom_target.rfind('.')
        if start_pos > 0:
            short_dom = nodom_target[start_pos+1:]
        else:
            short_dom = nodom_target

        new_target['url'] = short_dom
        new_target['description'] = "HostProcessor generated filename"
        database.files.append(new_target)
        added += 1

        new_target = new_target.copy()
        new_target['url'] = short_dom + 'admin'
        database.files.append(new_target)
        added += 1

        new_target = new_target.copy()
        new_target['url'] = short_dom + '-admin'
        database.files.append(new_target)
        added += 1

    # flatten subdomains
    target = target.replace('.', '')
    new_target = conf.path_template.copy()
    new_target['url'] = target
    new_target['description'] = "HostProcessor generated filename"
    database.files.append(new_target)
    added += 1

    textutils.output_info(" - HostProcessor Plugin: added " + str(added) + " new filenames")
