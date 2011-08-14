#!/usr/bin/python
#
# Tachyon - Fast Multi-Threaded Web Discovery Tool
# Copyright (c) 2011 Gabriel Tremblay - initnull hat gmail.com
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
#

from core import conf, database, loaders, utils
from core.workers import FetchUrlWorker, PrintWorker
from plugins import host, path

if __name__ == "__main__":
    # Spawn synchronized print output worker
    print_worker = PrintWorker()
    print_worker.daemon = True
    print_worker.start()

    # Ensure the host is of the right format
    utils.sanitize_config()

    # Load Paths
    utils.output('Loading target paths')
    loaders.load_path_file('data/path.lst')

    # Load files
    utils.output('Mixing path with target files')
    loaders.load_file_list('data/file.lst')

    # Import and run host plugins
    utils.output('Running ' + str(len(host.__all__)) + ' Host Plugins')
    for plugin_name in host.__all__:
        plugin = __import__ ("plugins.host." + plugin_name, fromlist=[plugin_name])
        if hasattr(plugin , 'execute'):
             plugin.execute()

    # Import and run file plugins
    utils.output('Running ' + str(len(path.__all__)) + ' File Plugins')
    for plugin_name in path.__all__:
        plugin = __import__ ("plugins.path." + plugin_name, fromlist=[plugin_name])
        if hasattr(plugin , 'execute'):
             plugin.execute()

    exit(0)


    # Spawn workers
    for thread_id in range(conf.thread_count):
        worker = FetchUrlWorker(thread_id)
        worker.daemon = True
        worker.start()

    # Fill work queue with fetch list
    utils.output('Filling work queue')
    for item in database.preload_list:
        database.fetch_queue.put(item)

    # Free some memory
    database.preload_list = None

    # Wait for task completion
    database.fetch_queue.join()

    # Wait for output completion
    database.output_queue.join()

