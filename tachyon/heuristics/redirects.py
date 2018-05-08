import re
from difflib import SequenceMatcher
from urllib.parse import urlparse

from hammertime.rules.redirects import valid_redirects
from hammertime.ruleset import RejectRequest


class RedirectLimiter:

    def __init__(self, sequence_matching=True):
        self.sequence_matching = sequence_matching
        self.digits = re.compile(r'\d+')
        self.not_found = re.compile(r'not[-_]*found', re.I)

    async def after_headers(self, entry):
        if entry.response.code not in valid_redirects:
            return

        location = entry.response.headers.get("location")
        if not location:
            return

        if "404" in self.digits.findall(location):
            raise RejectRequest("Redirection to error page.")
        if self.not_found.search(location):
            raise RejectRequest("Redirection to error page.")

        if self.sequence_matching and self._sequences_differ(entry.request.url, location):
            raise RejectRequest("Redirection to unrelated path.")

    def _sequences_differ(self, request, redirect):
        a = urlparse(request).path
        b = urlparse(redirect).path

        matcher = SequenceMatcher(isjunk=None, a=a, b=b, autojunk=False)
        return round(matcher.ratio(), 1) <= 0.8
