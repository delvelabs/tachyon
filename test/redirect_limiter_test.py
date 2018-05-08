from unittest import TestCase

from fixtures import async
from hammertime.http import Entry, StaticResponse
from hammertime.ruleset import RejectRequest

from tachyon.heuristics import RedirectLimiter


def redirect(url, redirect_to):
    return Entry.create(url, response=StaticResponse(302, headers={
        "location": redirect_to,
    }))


class RedirectLimiterTest(TestCase):

    @async()
    async def test_obvious_redirect_to_404(self):
        limiter = RedirectLimiter(sequence_matching=False)
        with self.assertRaises(RejectRequest):
            entry = redirect("http://example.com/foobar", redirect_to="http://example.com/404.php")
            await limiter.after_headers(entry)

    @async()
    async def test_full_matches_only(self):
        limiter = RedirectLimiter(sequence_matching=False)
        await limiter.after_headers(redirect("http://example.com/foobar", redirect_to="http://example.com/foobar/1404"))
        await limiter.after_headers(redirect("http://example.com/foobar", redirect_to="http://example.com/foobar/4041"))

    @async()
    async def test_obvious_redirect_to_not_found(self):
        limiter = RedirectLimiter(sequence_matching=False)
        with self.assertRaises(RejectRequest):
            entry = redirect("http://example.com/foobar", redirect_to="http://example.com/not-found")
            await limiter.after_headers(entry)

    @async()
    async def test_reject_wildely_different_paths(self):
        limiter = RedirectLimiter()
        with self.assertRaises(RejectRequest):
            await limiter.after_headers(redirect("http://example.com/foobar",
                                                 redirect_to="http://example.com/hello-world"))

    @async()
    async def test_accept_similar_paths(self):
        limiter = RedirectLimiter()
        await limiter.after_headers(redirect("http://example.com/foobar", redirect_to="http://example.com/foobar/"))

    @async()
    async def test_with_relative_paths(self):
        limiter = RedirectLimiter()
        await limiter.after_headers(redirect("http://example.com/foobar", redirect_to="foobar/"))
        await limiter.after_headers(redirect("http://example.com/foobar", redirect_to="/foobar/"))
