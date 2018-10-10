import asyncio
import json
import uuid
from os.path import join

from hammertime.utils.har import HammerTimeToHAR
from marshmallow_har import HAR, Creator
from tachyon.__version__ import __version__


class FileWriter:

    def __init__(self, output_dir):
        self.dir = output_dir

    def __call__(self, har: HAR):
        filename = "%s.har" % uuid.uuid4()
        file_path = join(self.dir, filename)
        with open(file_path, "w") as fp:
            fp.write(json.dumps(har.dump().data, indent=4))
        return file_path


class StoreHAR:

    def __init__(self, writer):
        self.writer = writer
        self.converter = HammerTimeToHAR()

    async def on_request_successful(self, entry):
        await asyncio.get_event_loop().run_in_executor(None, self._write_har, entry)

    def _write_har(self, entry):
        har = self.converter.convert_entries([entry], creator=Creator(name="Tachyon", version=__version__))
        entry.result.har_location = self.writer(har)
