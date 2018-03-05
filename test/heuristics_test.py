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


from unittest import TestCase
from unittest.mock import patch, MagicMock
from hammertime.http import Entry, StaticResponse
from hammertime.kb import KnowledgeBase
from hammertime.ruleset import RejectRequest

from tachyon.core.heuristics import FilterQueries
from fixtures import async, FakeHammerTimeEngine


class TestFilterQueries(TestCase):

    def setUp(self):
        self.engine = FakeHammerTimeEngine()
        self.filter = FilterQueries()
        self.filter.set_child_heuristics(None)
        self.filter.set_engine(self.engine)
        self.kb = KnowledgeBase()
        self.filter.set_kb(self.kb)

    @async()
    async def test_after_response_take_a_sample_with_a_junk_query(self):
        entry = Entry.create("http://example.com/?wsdl", response="not none")
        self.engine.mock.perform_high_priority.return_value = None

        with patch("tachyon.core.heuristics.uuid4", MagicMock(return_value="random-uuid-abc123")):
            await self.filter.after_response(entry)

            self.engine.mock.perform_high_priority.assert_called_once_with(
                Entry.create("http://example.com/?random-uuid-abc123"), self.filter.child_heuristics)

    @async()
    async def test_after_response_does_nothing_if_no_query_in_url(self):
        entry = Entry.create("http://example.com/index.php")

        await self.filter.after_response(entry)

        self.engine.mock.perform_high_priority.assert_not_called()

    @async()
    async def test_after_response_store_samples_in_kb(self):
        root_path = Entry.create("http://example.com/?wsdl", response=StaticResponse(200, {}))
        root_path_response = StaticResponse(200, {}, "homepage data")
        admin_path = Entry.create("http://example.com/admin/?wsdl", response=StaticResponse(200, {}))
        admin_path_response = StaticResponse(200, {}, "admin data")
        images_path = Entry.create("http://example.com/images/?wsdl", response=StaticResponse(200, {}))
        images_path_response = StaticResponse(200, {}, "images...")
        login_file = Entry.create("http://example.com/login.php?login", response=StaticResponse(200, {}))
        login_file_response = StaticResponse(200, {}, "login page")
        self.engine.mock.perform_high_priority.side_effect = [root_path_response, admin_path_response,
                                                              images_path_response, login_file_response]

        await self.filter.after_response(root_path)
        await self.filter.after_response(admin_path)
        await self.filter.after_response(images_path)
        await self.filter.after_response(login_file)

        self.assertEqual(self.kb.query_samples["example.com/"], root_path_response)
        self.assertEqual(self.kb.query_samples["example.com/admin/"], admin_path_response)
        self.assertEqual(self.kb.query_samples["example.com/images/"], images_path_response)
        self.assertEqual(self.kb.query_samples["example.com/login.php"], login_file_response)

    @async()
    async def test_after_response_use_existing_sample(self):
        initial_sample = StaticResponse(200, {}, "response content")
        self.kb.query_samples["example.com/"] = initial_sample
        entry = Entry.create("http://example.com/?wsdl", response=StaticResponse(200, {}, "content 123"))

        await self.filter.after_response(entry)

        self.engine.mock.perform_high_priority.assert_not_called()
        self.assertEqual(self.kb.query_samples["example.com/"], initial_sample)

    @async()
    async def test_after_response_reject_request_if_entry_response_equals_sample_response(self):
        sample = StaticResponse(200, {}, "response content")
        self.kb.query_samples["example.com/"] = sample
        entry = Entry.create("http://example.com/?wsdl", response=StaticResponse(200, {}, "response content"))

        with self.assertRaises(RejectRequest):
            await self.filter.after_response(entry)
