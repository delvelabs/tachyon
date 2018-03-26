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


from unittest import TestCase
from unittest.mock import patch, MagicMock, call
from hammertime.http import Entry, StaticResponse
from hammertime.kb import KnowledgeBase
from hammertime.ruleset import RejectRequest
from hammertime.rules.simhash import Simhash
from hammertime.engine.aiohttp import Response
import hashlib
import binascii

from tachyon.core.heuristics import RejectIgnoredQuery, LogBehaviorChange, MatchString
from fixtures import async, FakeHammerTimeEngine, create_json_data


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

        with patch("tachyon.core.heuristics.uuid4", MagicMock(return_value="random-uuid-abc123")):
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

        with patch("tachyon.core.heuristics.Simhash", FakeSimhash):
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

        with patch("tachyon.core.heuristics.Simhash") as Simhash:
            await self.filter.after_response(Entry.create("http://example.com/?wsdl", response=response))

            Simhash.assert_not_called()

    @async()
    async def test_content_that_is_text_never_match_sample_that_contains_md5(self):
        self.kb.query_samples["example.com/"] = {"md5": "12345"}
        response = StaticResponse(200, {}, "content")

        with patch("tachyon.core.heuristics.hashlib") as hashlib:
            await self.filter.after_response(Entry.create("http://example.com/?wsdl", response=response))

            hashlib.md5.assert_not_called()

    def hash(self, response):
        return {"simhash": FakeSimhash(response.content).value}


class TestLogBehaviorChange(TestCase):

    @async()
    async def test_update_current_behavior_state(self):
        log_behavior_change = LogBehaviorChange()
        log_behavior_change.is_behavior_normal = True
        entry = Entry.create("http://example.com/")

        entry.result.error_behavior = True
        await log_behavior_change.after_response(entry)
        self.assertFalse(log_behavior_change.is_behavior_normal)

        entry.result.error_behavior = False
        await log_behavior_change.after_response(entry)
        self.assertTrue(log_behavior_change.is_behavior_normal)

    @async()
    async def test_log_message_if_behavior_was_normal_and_entry_is_flagged_has_error_behavior(self):
        log_behavior_change = LogBehaviorChange()
        entry = Entry.create("http://example.com/")
        entry.result.error_behavior = True

        with patch("tachyon.core.heuristics.output_info") as output_info:
            await log_behavior_change.after_response(entry)

            output_info.assert_called_once_with("Behavior change detected! Results may be incomplete or tachyon may "
                                                "never exit.")

    @async()
    async def test_log_message_if_behavior_is_restored_to_normal(self):
        log_behavior_change = LogBehaviorChange()
        log_behavior_change.is_behavior_normal = False
        entry = Entry.create("http://example.com/")
        entry.result.error_behavior = False

        with patch("tachyon.core.heuristics.output_info") as output_info:
            await log_behavior_change.after_response(entry)

            output_info.assert_called_once_with("Normal behavior seems to be restored.")

    @async()
    async def test_messages_are_only_logged_once(self):
        log_behavior_change = LogBehaviorChange()
        entry = Entry.create("http://example.com/")
        entry.result.error_behavior = True

        with patch("tachyon.core.heuristics.output_info") as output_info:
            await log_behavior_change.after_response(entry)
            await log_behavior_change.after_response(entry)
            entry.result.error_behavior = False
            await log_behavior_change.after_response(entry)
            await log_behavior_change.after_response(entry)

            output_info.assert_has_calls([call("Behavior change detected! Results may be incomplete or tachyon may "
                                               "never exit."), call("Normal behavior seems to be restored.")])


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


class FakeSimhash:

    def __init__(self, data, *args, **kwargs):
        self.value = "simhash of %s" % data

    def distance(self, *args):
        return 999
