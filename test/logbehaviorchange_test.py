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
from unittest.mock import patch, call

from fixtures import async
from hammertime.http import Entry

from tachyon.heuristics import LogBehaviorChange


class TestLogBehaviorChange(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.patcher = patch("tachyon.textutils.output_manager")
        cls.patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.patcher.stop()

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

        with patch("tachyon.heuristics.logbehaviorchange.output_info") as output_info:
            await log_behavior_change.after_response(entry)

            output_info.assert_called_once_with("Behavior change detected! Results may be incomplete or tachyon may "
                                                "never exit.")

    @async()
    async def test_log_message_if_behavior_is_restored_to_normal(self):
        log_behavior_change = LogBehaviorChange()
        log_behavior_change.is_behavior_normal = False
        entry = Entry.create("http://example.com/")
        entry.result.error_behavior = False

        with patch("tachyon.heuristics.logbehaviorchange.output_info") as output_info:
            await log_behavior_change.after_response(entry)

            output_info.assert_called_once_with("Normal behavior seems to be restored.")

    @async()
    async def test_messages_are_only_logged_once(self):
        log_behavior_change = LogBehaviorChange()
        entry = Entry.create("http://example.com/")
        entry.result.error_behavior = True

        with patch("tachyon.heuristics.logbehaviorchange.output_info") as output_info:
            await log_behavior_change.after_response(entry)
            await log_behavior_change.after_response(entry)
            entry.result.error_behavior = False
            await log_behavior_change.after_response(entry)
            await log_behavior_change.after_response(entry)

            output_info.assert_has_calls([call("Behavior change detected! Results may be incomplete or tachyon may "
                                               "never exit."), call("Normal behavior seems to be restored.")])
