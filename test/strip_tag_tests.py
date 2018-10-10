import unittest
from tachyon.heuristics import StripTag
from hammertime.http import Entry, StaticResponse
from fixtures import async_test


class StripTagTest(unittest.TestCase):

    def entry(self, content):
        return Entry.create("http://example.com/", response=StaticResponse(200, content=content, headers={}))

    @async_test()
    async def test_content_left_intact(self, loop):
        entry = self.entry("Hello World")
        await StripTag("input").after_response(entry)

        self.assertEqual("Hello World", entry.response.content)

    @async_test()
    async def test_complete_tags_are_removed(self, loop):
        entry = self.entry('<html><input> test <input name="123" value="abc"/> </html>')
        await StripTag("input").after_response(entry)

        self.assertEqual("<html><input> test <input> </html>", entry.response.content)

    @async_test()
    async def test_leave_other_tags_intact(self, loop):
        entry = self.entry('<html><input> test <script name="123" value="abc"/> </html>')
        await StripTag("input").after_response(entry)

        self.assertEqual('<html><input> test <script name="123" value="abc"/> </html>', entry.response.content)
