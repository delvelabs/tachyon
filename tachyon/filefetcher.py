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


import asyncio
from urllib.parse import urljoin

from hammertime.rules.deadhostdetection import OfflineHostException
from hammertime.rules.redirects import valid_redirects
from hammertime.ruleset import StopRequest, RejectRequest

from tachyon.textutils import output_found


class FileFetcher:

    def __init__(self, host, hammertime):
        self.host = host
        self.hammertime = hammertime

    async def fetch_files(self, file_list):
        requests = []
        for file in file_list:
            url = urljoin(self.host, file["url"])
            requests.append(self.hammertime.request(url, arguments={"file": file}))
        for future in asyncio.as_completed(requests):
            try:
                entry = await future
                if self._is_entry_invalid(entry):
                    continue
                if entry.response.code == 500:
                    self.output_found(entry, message_prefix="ISE, ")
                elif entry.response.code not in valid_redirects:
                    if len(entry.response.raw) == 0:
                        self.output_found(entry, message_prefix="Empty ")
                    else:
                        self.output_found(entry)
            except OfflineHostException:
                raise
            except RejectRequest:
                pass
            except StopRequest:
                continue

    def output_found(self, entry, message_prefix=""):
        url = entry.request.url
        file = entry.arguments["file"]
        message = "{prefix}{desc} at: {url}".format(prefix=message_prefix, desc=file["description"], url=url)
        data = {"url": url, "description": file["description"], "code": entry.response.code,
                "severity": file.get('severity', "warning")}
        output_found(message, data=data)

    def _is_entry_invalid(self, entry):
        if entry.result.string_match:
            return False
        return entry.result.soft404 or entry.result.error_behavior
