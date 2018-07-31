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


import binascii


class MatchString:

    async def before_request(self, entry):
        entry.result.string_match = False

    async def after_response(self, entry):
        if "file" in entry.arguments:
            if "match_string" in entry.arguments["file"]:
                string = entry.arguments["file"]["match_string"]
                entry.result.string_match = string in entry.response.content
            elif "match_bytes" in entry.arguments["file"]:
                raw_hex_string = entry.arguments["file"]["match_bytes"].encode("utf-8")
                raw_string = binascii.unhexlify(raw_hex_string)
                entry.result.string_match = raw_string in entry.response.raw
            else:
                entry.result.string_match = False
