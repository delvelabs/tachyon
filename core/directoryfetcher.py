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


from urllib.parse import urljoin
import asyncio
from hammertime.ruleset import RejectRequest, StopRequest

from core import database, stats


class DirectoryFetcher:

    def __init__(self, target_host, hammertime):
        self.target_host = target_host
        self.hammertime = hammertime

    async def fetch_paths(self, paths):
        requests = []
        for path in paths:
            url = urljoin(self.target_host, path["url"])
            requests.append(self.hammertime.request(url, arguments={"path": path}))
        done, pending = await asyncio.wait(requests, loop=self.hammertime.loop, return_when=asyncio.ALL_COMPLETED)
        for future in done:
            try:
                entry = await future
                database.valid_paths.append(entry.arguments["path"])
            except RejectRequest:
                pass
            except StopRequest:
                continue
            # TODO replace with hammertime.stats when migration is complete.
            stats.update_processed_items()
