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
from unittest import TestCase

from fixtures import async, create_json_data
from hammertime.http import Entry, StaticResponse

from tachyon.heuristics import MatchString


class TestMatchString(TestCase):

    @async()
    async def test_set_string_match_flag_in_entry_result_to_true_if_string_to_match_found_in_response_content(self):
        file_to_fetch = create_json_data(["file"], match_string="abc123")[0]
        match_string = MatchString()
        response = StaticResponse(200, {}, content="test abc123 test")
        entry = Entry.create("http://example.com/file", arguments={"file": file_to_fetch}, response=response)

        await match_string.after_response(entry)

        self.assertTrue(entry.result.string_match)

    @async()
    async def test_set_string_match_flag_in_entry_result_to_false_if_string_to_match_found_in_response_content(self):
        file_to_fetch = create_json_data(["file"], match_string="abc123")[0]
        match_string = MatchString()
        response = StaticResponse(200, {}, content="Content is not matching")
        entry = Entry.create("http://example.com/file", arguments={"file": file_to_fetch}, response=response)

        await match_string.after_response(entry)

        self.assertFalse(entry.result.string_match)

    @async()
    async def test_set_string_match_to_false_if_no_match_string_in_file(self):
        file_to_fetch = create_json_data(["file"])[0]
        match_string = MatchString()
        response = StaticResponse(200, {}, content="content")
        entry = Entry.create("http://example.com/file", arguments={"file": file_to_fetch}, response=response)

        await match_string.after_response(entry)

        self.assertFalse(entry.result.string_match)

    @async()
    async def test_only_add_string_match_flag_for_file(self):
        path = create_json_data(["/path/"])[0]
        match_string = MatchString()
        response = StaticResponse(200, {}, content="")
        entry = Entry.create("http://example.com/file", arguments={"path": path}, response=response)

        await match_string.after_response(entry)

        self.assertFalse(hasattr(entry.result, "string_match"))

    @async()
    async def test_match_bytes_with_string(self):
        bytes_as_string = binascii.hexlify(b"abc123").decode("utf-8")
        file_to_fetch = create_json_data(["file"], match_bytes=bytes_as_string)[0]
        match_string = MatchString()
        response = StaticResponse(200, {}, content="abc123")
        entry = Entry.create("http://example.com/file", arguments={"file": file_to_fetch}, response=response)

        await match_string.after_response(entry)

        self.assertTrue(entry.result.string_match)

    @async()
    async def test_match_bytes_with_binary_response(self):
        file_to_fetch = create_json_data(["file"], match_bytes="0102030405060708090a0b0c0d0e0f10")[0]
        match_string = MatchString()
        response = StaticResponse(200, {})
        response.raw = b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f\x10\x11\x12\x13\x14\x15'
        entry = Entry.create("http://example.com/file", arguments={"file": file_to_fetch}, response=response)

        await match_string.after_response(entry)

        self.assertTrue(entry.result.string_match)
