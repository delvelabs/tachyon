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


import hashlib
from unittest import TestCase
from unittest.mock import patch, MagicMock

from fixtures import async, FakeHammerTimeEngine
from hammertime.engine.aiohttp import Response
from hammertime.http import Entry, StaticResponse
from hammertime.kb import KnowledgeBase
from hammertime.rules.simhash import Simhash
from hammertime.ruleset import RejectRequest

from tachyon.heuristics import RejectIgnoredQuery


class TestRejectIgnoredQuery(TestCase):

    def setUp(self):
        self.engine = FakeHammerTimeEngine()
        self.filter = RejectIgnoredQuery()
        self.filter.set_child_heuristics(None)
        self.filter.set_engine(self.engine)
        self.kb = KnowledgeBase()
        self.filter.set_kb(self.kb)

    @async()
    async def test_after_response_take_a_sample_with_a_junk_query(self):
        response = StaticResponse(200, {}, "content")
        entry = Entry.create("http://example.com/?wsdl", response=StaticResponse(200, {}, "not same content"))
        self.engine.mock.perform_high_priority.return_value = response

        with patch("tachyon.heuristics.rejectignoredquery.uuid4", MagicMock(return_value="random-uuid-abc123")):
            await self.filter.after_response(entry)

            self.engine.mock.perform_high_priority.assert_called_once_with(
                Entry.create("http://example.com/?random-uuid-abc123", response=response), self.filter.child_heuristics)

    @async()
    async def test_after_response_does_nothing_if_no_query_in_url(self):
        entry = Entry.create("http://example.com/index.php")

        await self.filter.after_response(entry)

        self.engine.mock.perform_high_priority.assert_not_called()

    @async()
    async def test_after_response_store_samples_in_kb(self):
        root_path = Entry.create("http://example.com/?wsdl", response=StaticResponse(200, {}, "123"))
        root_path_response = StaticResponse(200, {}, "homepage data")
        admin_path = Entry.create("http://example.com/admin/?wsdl", response=StaticResponse(200, {}, "123"))
        admin_path_response = StaticResponse(200, {}, "admin data")
        images_path = Entry.create("http://example.com/images/?wsdl", response=StaticResponse(200, {}, "123"))
        images_path_response = StaticResponse(200, {}, "images...")
        login_file = Entry.create("http://example.com/login.php?login", response=StaticResponse(200, {}, "123"))
        login_file_response = StaticResponse(200, {}, "login page")
        self.engine.mock.perform_high_priority.side_effect = [root_path_response, admin_path_response,
                                                              images_path_response, login_file_response]

        with patch("tachyon.heuristics.rejectignoredquery.Simhash", FakeSimhash):
            await self.filter.after_response(root_path)
            await self.filter.after_response(admin_path)
            await self.filter.after_response(images_path)
            await self.filter.after_response(login_file)

            self.assertEqual(self.kb.query_samples["example.com/"], self.hash(root_path_response))
            self.assertEqual(self.kb.query_samples["example.com/admin/"], self.hash(admin_path_response))
            self.assertEqual(self.kb.query_samples["example.com/images/"], self.hash(images_path_response))
            self.assertEqual(self.kb.query_samples["example.com/login.php"], self.hash(login_file_response))

    @async()
    async def test_after_response_use_existing_sample(self):
        initial_sample = "hash of response content"
        self.kb.query_samples["example.com/"] = initial_sample
        entry = Entry.create("http://example.com/?wsdl", response=StaticResponse(200, {}, "content 123"))

        await self.filter.after_response(entry)

        self.engine.mock.perform_high_priority.assert_not_called()
        self.assertEqual(self.kb.query_samples["example.com/"], initial_sample)

    @async()
    async def test_after_response_reject_request_if_simhash_of_response_content_equals_sample_simhash(self):
        self.kb.query_samples["example.com/"] = {"simhash": Simhash("response content").value}
        entry = Entry.create("http://example.com/?wsdl", response=StaticResponse(200, {}, "response content"))
        slightly_different_response = Entry.create("http://example.com/?wsdl",
                                                   response=StaticResponse(200, {}, "response-content"))

        with self.assertRaises(RejectRequest):
            await self.filter.after_response(entry)
        with self.assertRaises(RejectRequest):
            await self.filter.after_response(slightly_different_response)

    @async()
    async def test_add_hash_of_raw_content_if_response_content_of_sample_is_not_text(self):
        bytes = b'Invalid UTF8 x\x80Z"'
        sample_response = Response(200, {})
        sample_response.set_content(bytes, True)
        self.engine.mock.perform_high_priority.return_value = sample_response

        await self.filter.after_response(Entry.create("http://example.com/?wsdl",
                                                      response=StaticResponse(200, {}, "123")))

        self.assertEqual(self.kb.query_samples["example.com/"], {"md5": hashlib.md5(bytes).digest()})

    @async()
    async def test_content_that_is_not_text_never_match_content_simhash_of_sample(self):
        raw = b'Invalid UTF8 x\x80Z"'
        response = Response(200, {})
        response.set_content(raw, True)
        hash = self.filter._hash_response(StaticResponse(200, {}, "content"))
        self.kb.query_samples["example.com/"] = {"simhash": hash}

        with patch("tachyon.heuristics.rejectignoredquery.Simhash") as Simhash:
            await self.filter.after_response(Entry.create("http://example.com/?wsdl", response=response))

            Simhash.assert_not_called()

    @async()
    async def test_content_that_is_text_never_match_sample_that_contains_md5(self):
        self.kb.query_samples["example.com/"] = {"md5": "12345"}
        response = StaticResponse(200, {}, "content")

        with patch("tachyon.heuristics.rejectignoredquery.hashlib") as hashlib:
            await self.filter.after_response(Entry.create("http://example.com/?wsdl", response=response))

            hashlib.md5.assert_not_called()

    def hash(self, response):
        return {"simhash": FakeSimhash(response.content).value}


class FakeSimhash:

    def __init__(self, data, *args, **kwargs):
        self.value = "simhash of %s" % data

    def distance(self, *args):
        return 999
