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


from tachyon.textutils import output_info


class LogBehaviorChange:

    MESSAGE = "Behavior change detected! The above results are known to be unreliable. " \
              "Re-validation will occur at the end of the scan."

    def __init__(self):
        self.has_error = False

    async def after_response(self, entry):
        if not self.has_error and entry.result.error_behavior:
            self.has_error = True
            output_info(self.MESSAGE)
