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
import logging
from datetime import datetime

import click

from tachyon import conf
from tachyon.__version__ import __version__

FOUND = logging.INFO + 5
TIMEOUT = logging.WARNING + 5
logging.addLevelName(FOUND, "FOUND")
logging.addLevelName(TIMEOUT, "TIMEOUT")


class OutputManager:

    def output_result(self, text, data=None):
        self._add_output(text, FOUND, data)

    def output_info(self, text):
        self._add_output(text, logging.INFO)

    def output_error(self, text):
        self._add_output(text, logging.ERROR)

    def output_timeout(self, text):
        self._add_output(text, TIMEOUT)

    def output_raw_message(self, message):
        click.echo(message)

    def output_header(self):
        pass

    def flush(self):
        raise NotImplementedError

    def _add_output(self, text, level, data=None):
        raise NotImplementedError

    def _format_output(self, time, level_name, text, data):
        raise NotImplementedError

    def _get_current_time(self):
        return str(datetime.now().strftime("%H:%M:%S"))


class JSONOutput(OutputManager):

    def __init__(self):
        self.buffer = []

    def flush(self):
        self.output_raw_message(json.dumps({"result": self.buffer, "version": __version__, "from": conf.name}))

    def _add_output(self, text, level, data=None):
        formatted = self._format_output(self._get_current_time(), logging.getLevelName(level), text, data)
        self.buffer.append(formatted)

    def _format_output(self, time, level_name, text, data):
        output = {"type": level_name.lower(), "text": text, "time": time}
        if data is not None:
            output.update(**data)
        return output


class PrettyOutput(OutputManager):

    def flush(self):
        pass

    def output_header(self):
        """ Print a _cute_ program header """
        header = "\n\t Tachyon v%s - Fast Multi-Threaded Web Discovery Tool\n\t https://github.com/delvelabs/tachyon\n"
        self.output_raw_message(header % __version__)

    def _add_output(self, text, level, data=None):
        formatted = self._format_output(self._get_current_time(), logging.getLevelName(level), text, data)
        self.output_raw_message(formatted)

    def _format_output(self, time, level_name, text, data):
        output_format = "[{time}] [{level}] {text}"
        output = output_format.format(time=time, level=level_name, text=text)
        return output
