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


import json
from unittest import TestCase
from unittest.mock import MagicMock, patch, call

from freezegun import freeze_time

from tachyon.output import JSONOutput, PrettyOutput, __version__


class TestJSONOutput(TestCase):

    @freeze_time("2018-04-11 12:00:00")
    def test_output_result_add_found_to_buffer(self):
        url = "http://example.com/y"
        result = "File x found at " + url
        data = {"url": url, "severity": "critical", "description": "File x desc", "code": 200}
        output = JSONOutput()

        output.output_result(result, data=data)

        self.assertEqual(output.buffer, [{"type": "found", "url": url, "code": 200, "text": result,
                                         "severity": "critical", "description": "File x desc", "time": "12:00:00"}])

    @freeze_time("2018-04-11 12:00:00")
    def test_output_info_add_message_with_level_info_to_buffer(self):
        message = "information..."
        output = JSONOutput()

        output.output_info(message)

        self.assertEqual(output.buffer, [{"type": "info", "text": message, "time": "12:00:00"}])

    @freeze_time("2018-04-11 12:00:00")
    def test_output_error_add_message_with_level_error_to_buffer(self):
        message = "!!!ERROR!!!"
        output = JSONOutput()

        output.output_error(message)

        self.assertEqual(output.buffer, [{"type": "error", "text": message, "time": "12:00:00"}])

    @freeze_time("2018-04-11 12:00:00")
    def test_output_timeout_add_message_with_level_timeout_to_buffer(self):
        message = "timeout"
        output = JSONOutput()

        output.output_timeout(message)

        self.assertEqual(output.buffer, [{"type": "timeout", "text": message, "time": "12:00:00"}])

    @freeze_time("2018-04-11 12:00:00")
    def test_flush_output_buffer_content_as_json(self):
        message = "information..."
        output = JSONOutput()
        output.output_info(message)
        output.output_raw_message = MagicMock()

        output.flush()

        expected = {"from": "delvelabs/tachyon", "version": __version__, "result": [
            {"text": "information...", "time": "12:00:00", "type": "info"}]}
        actual = output.output_raw_message.call_args[0][0]
        self.assertEqual(json.loads(actual), expected)


@freeze_time("2018-04-11 12:00:00")
class TestPrettyOutput(TestCase):

    def setUp(self):
        self.output = PrettyOutput()

    def test_output_result_add_found_to_result_buffer(self):
        url = "http://example.com/y"
        result = "File x found at " + url
        data = {"url": url, "severity": "critical", "description": "File x desc", "code": 200}
        output = PrettyOutput()

        output.output_result(result, data=data)

        self.assertEqual(output.result_buffer, ["[12:00:00] [FOUND] %s" % result])

    @patch("tachyon.output.click")
    def test_output_info_print_message_with_level_info(self, click):
        message = "information..."

        self.output.output_info(message)

        click.echo.assert_called_once_with("[12:00:00] [INFO] information...")

    @patch("tachyon.output.click")
    def test_output_error_print_message_with_level_error(self, click):
        message = "ERROR!!!"

        self.output.output_error(message)

        click.echo.assert_called_once_with("[12:00:00] [ERROR] ERROR!!!")

    @patch("tachyon.output.click")
    def test_output_info_print_message_with_level_timeout(self, click):
        message = "timeout..."

        self.output.output_timeout(message)

        click.echo.assert_called_once_with("[12:00:00] [TIMEOUT] timeout...")

    @patch("tachyon.output.click")
    def test_flush_print_message_in_found_buffer(self, click):
        url = "http://example.com/y"
        found0 = "File x found at " + url
        found1 = "File z found at " + url
        self.output.output_result(found0)
        self.output.output_result(found1)

        self.output.flush()

        click.echo.assert_has_calls([call("[12:00:00] [FOUND] %s" % found0), call("[12:00:00] [FOUND] %s" % found1)])
