from unittest import TestCase
from unittest.mock import MagicMock
from tachyon.result import ResultAccumulator
from hammertime.http import Entry, StaticResponse


class ResultAccumulatorTest(TestCase):

    def test_add_entry(self):
        entry = Entry.create(url="http://example.com/passwd",
                             arguments={
                               "file": {
                                   "description": "password",
                                   "severity": "critical",
                               }
                             },
                             response=StaticResponse(200, content="hello", headers={}))

        manager = MagicMock()

        acc = ResultAccumulator(output_manager=manager)
        acc.add_entry(entry)

        manager.output_result.assert_called_with("password at: http://example.com/passwd", data={
            "url": "http://example.com/passwd",
            "description": "password",
            "code": 200,
            "severity": "critical",
        })

    def test_add_empty_entry(self):
        entry = Entry.create(url="http://example.com/passwd",
                             arguments={
                               "file": {
                                   "description": "password",
                                   "severity": "critical",
                               }
                             },
                             response=StaticResponse(200, content="", headers={}))

        manager = MagicMock()

        acc = ResultAccumulator(output_manager=manager)
        acc.add_entry(entry)

        manager.output_result.assert_called_with("Empty password at: http://example.com/passwd", data={
            "url": "http://example.com/passwd",
            "description": "password",
            "code": 200,
            "severity": "critical",
        })

    def test_path_entry(self):
        entry = Entry.create(url="http://example.com/private/",
                             arguments={
                               "path": {
                                   "description": "private",
                                   "severity": "medium",
                               }
                             },
                             response=StaticResponse(401, content="", headers={}))

        manager = MagicMock()

        acc = ResultAccumulator(output_manager=manager)
        acc.add_entry(entry)

        manager.output_result.assert_called_with("Password Protected - private at: http://example.com/private/", data={
            "url": "http://example.com/private/",
            "description": "private",
            "code": 401,
            "severity": "medium",
        })

    def test_tomcat_redirect_detected(self):
        entry = Entry.create(url="http://example.com/private/",
                             arguments={
                               "path": {
                                   "description": "private",
                                   "severity": "medium",
                               }
                             },
                             response=StaticResponse(404, content="Apache Tomcat/", headers={}))

        manager = MagicMock()

        acc = ResultAccumulator(output_manager=manager)
        acc.add_entry(entry)

        manager.output_result.assert_called_with("Tomcat redirect, private at: http://example.com/private/", data={
            "url": "http://example.com/private/",
            "description": "private",
            "code": 404,
            "severity": "medium",
            "special": "tomcat-redirect",
        })
