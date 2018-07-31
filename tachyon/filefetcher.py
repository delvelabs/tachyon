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
from hammertime.ruleset import StopRequest, RejectRequest

from .textutils import output_manager, PrettyOutput
from .result import ResultAccumulator


class FileFetcher:

    def __init__(self, host, hammertime, accumulator=None):
        self.host = host
        self.hammertime = hammertime
        self.accumulator = accumulator or ResultAccumulator(output_manager=output_manager or PrettyOutput())

    async def fetch_files(self, file_list):
        for file in file_list:
            url = urljoin(self.host, file["url"])
            self.hammertime.request(url, arguments={"file": file})
        async for entry in self.hammertime.successful_requests():
            try:
                self.accumulator.add_entry(entry)
            except OfflineHostException:
                raise
            except RejectRequest:
                pass
            except StopRequest:
                continue


class ValidateEntry:
    """
    Combines the RejectSoft404 and RejectErrorBehavior, but excludes problems when
    the result requested a string match and found it.
    """

    async def after_response(self, entry):
        if entry.result.string_match:
            # We found what we were looking for, this entry has to be valid.
            return

        if getattr(entry.result, "error_behavior", False):
            raise StopRequest("Error behavior detected.")
        if getattr(entry.result, "soft404", False):
            raise RejectRequest("Soft 404 detected")
