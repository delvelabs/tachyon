from fixtures import async_test
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

    def test_add_without_arguments(self):
        entry = Entry.create(url="http://example.com/passwd",
                             response=StaticResponse(200, content="hello", headers={}))

        manager = MagicMock()

        acc = ResultAccumulator(output_manager=manager)
        acc.add_entry(entry)

        manager.output_result.assert_not_called()

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

    def test_redirection_should_provide_the_final_url_as_result(self):
        entry = Entry.create(url="http://example.com/private",
                             arguments={
                               "path": {
                                   "description": "private",
                                   "severity": "medium",
                               }
                             },
                             response=StaticResponse(200, content="Hello", headers={}))
        entry.result.redirects.append(Entry.create(url="http://example.com/private",
                                                   response=StaticResponse(302, content="", headers={
                                                    "Location": "/private/",
                                                   })))
        entry.result.redirects.append(Entry.create(url="http://example.com/private/",
                                                   response=StaticResponse(200, content="Hello", headers={})))

        manager = MagicMock()

        acc = ResultAccumulator(output_manager=manager)
        acc.add_entry(entry)

        manager.output_result.assert_called_with("private at: http://example.com/private/", data={
            "url": "http://example.com/private/",
            "description": "private",
            "code": 200,
            "severity": "medium",
        })

    @async_test()
    async def test_revalidation_reports_the_same_urls_as_confirmed(self, loop):
        manager = MagicMock()

        acc = ResultAccumulator(output_manager=manager)
        acc.add_entry(self._simple("backup", "http://example.com/backup.zip"))
        acc.add_entry(self._simple("ssh key", "http://example.com/.ssh/id_rsa"))
        manager.reset_mock()

        await acc.revalidate(NoRevalidate(accept=True))

        manager.output_result.assert_called_with("ssh key at: http://example.com/.ssh/id_rsa (Confirmed)", data={
            "url": "http://example.com/.ssh/id_rsa",
            "description": "ssh key",
            "code": 200,
            "severity": "warning",
            "confirmed": True,
        })

    @async_test()
    async def test_revalidation_can_reject(self, loop):
        manager = MagicMock()

        acc = ResultAccumulator(output_manager=manager)
        acc.add_entry(self._simple("backup", "http://example.com/backup.zip"))
        acc.add_entry(self._simple("ssh key", "http://example.com/.ssh/id_rsa"))
        manager.reset_mock()

        await acc.revalidate(NoRevalidate(accept=False))

        manager.output_result.assert_not_called()

    @async_test()
    async def test_result_contains_evidence(self, loop):
        manager = MagicMock()

        acc = ResultAccumulator(output_manager=manager)
        acc.add_entry(self._simple("backup", "http://example.com/backup.zip", har="/tmp/output/abc.har"))

        manager.output_result.assert_called_with(
            "backup at: http://example.com/backup.zip (HAR: /tmp/output/abc.har)",
            data={
                "url": "http://example.com/backup.zip",
                "description": "backup",
                "code": 200,
                "severity": "warning",
                "har": "/tmp/output/abc.har",
            })

    @staticmethod
    def _simple(description, url, har=None):
        entry = Entry.create(url=url,
                             arguments={
                               "file": {"description": description}
                             },
                             response=StaticResponse(200, content="Hello", headers={}))

        if har is not None:
            entry.result.har_location = har

        return entry


class NoRevalidate:

    def __init__(self, accept):
        self.accept = accept

    async def is_valid(self, entry):
        return self.accept
