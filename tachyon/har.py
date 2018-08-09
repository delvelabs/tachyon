import json
import uuid
from http.client import responses
from os.path import join

from marshmallow_har import HAR, Entry, Request, Response, Content, Header, Creator
from tachyon.__version__ import __version__


class FileWriter:

    def __init__(self, output_dir):
        self.dir = output_dir

    def __call__(self, har: HAR):
        filename = "%s.har" % uuid.uuid4()
        file_path = join(self.dir, filename)
        with open(file_path, "w") as fp:
            fp.write(json.dumps(har.dump().data))
        return file_path


class StoreHAR:

    def __init__(self, writer):
        self.writer = writer
        self.converter = HammerTimeToHAR()

    async def on_request_successful(self, entry):
        har = self.converter.convert_entries([entry])
        entry.result.har_location = self.writer(har)


class HammerTimeToHAR:

    def convert_entries(self, entries):
        out = HAR(creator=Creator(name="Tachyon", version=__version__))
        for e in entries:
            if e.result.redirects:
                for sub in e.result.redirects:
                    out.entries.append(self.convert_entry(sub))
            else:
                out.entries.append(self.convert_entry(e))
        return out

    def convert_entry(self, entry):
        out = Entry(request=self.convert_request(entry.request))

        if entry.response:
            out.response = self.convert_response(entry.response)

        return out

    def convert_headers(self, headers):
        return [Header(name=k, value=v) for k, v in headers.items()]

    def convert_request(self, request):
        out = Request(method=request.method, url=request.url,
                      headers=self.convert_headers(request.headers))

        return out

    def convert_response(self, response):
        out = Response(status=response.code, status_text=self._lookup_code_text(response.code),
                       headers=self.convert_headers(response.headers))
        out.content = Content(text=self._get_content(response))

        headers = {k.lower(): v for k, v in response.headers.items()}
        out.content.mime_type = headers.get('content-type')
        out.content.size = int(headers.get('size', -1))

        return out

    def _get_content(self, response):
        try:
            return response.content
        except UnicodeDecodeError:
            return response.raw.decode("utf-8", "surrogateescape")

    @staticmethod
    def _lookup_code_text(code):
        return responses.get(code) or "Unknown"
