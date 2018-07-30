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


from urllib.parse import urljoin

from hammertime.rules.deadhostdetection import OfflineHostException
from hammertime.ruleset import RejectRequest, StopRequest

from .textutils import output_manager, PrettyOutput
from .result import ResultAccumulator
from tachyon import database


class DirectoryFetcher:

    def __init__(self, target_host, hammertime, accumulator=None):
        self.target_host = target_host
        self.hammertime = hammertime
        self.accumulator = accumulator or ResultAccumulator(output_manager=output_manager or PrettyOutput())

    async def fetch_paths(self, paths):
        for path in paths:
            url = urljoin(self.target_host, path["url"])
            if url[-1] != "/":
                url += "/"
            self.hammertime.request(url, arguments={"path": path})
        async for entry in self.hammertime.successful_requests():
            try:
                if "path" not in entry.arguments:
                    continue

                if entry.response.code != 401:
                    database.valid_paths.append(entry.arguments["path"])
                if entry.arguments["path"]["url"] != "/":
                    self.accumulator.add_entry(entry)
            except OfflineHostException:
                raise
            except RejectRequest:
                pass
            except StopRequest:
                continue
