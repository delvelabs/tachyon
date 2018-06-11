import re


class StripTag:

    def __init__(self, tag_name):
        tag_name = tag_name.encode('utf-8')
        self.replacement = b'<%s>' % tag_name
        self.rule = re.compile(b'<%s\s[^>]+>' % tag_name)

    async def after_response(self, entry):
        entry.response.raw = self.rule.sub(self.replacement, entry.response.raw)
