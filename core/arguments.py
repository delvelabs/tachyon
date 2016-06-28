from optparse import OptionParser, Option, OptionValueError
from core import conf, textutils

class MultipleOption(Option):
    """
    Taken from the OptionParser documentation, slightly altered.
    """

    ACTIONS = Option.ACTIONS + ("extend",)
    STORE_ACTIONS = Option.STORE_ACTIONS + ("extend",)
    TYPED_ACTIONS = Option.TYPED_ACTIONS + ("extend",)
    ALWAYS_TYPED_ACTIONS = Option.ALWAYS_TYPED_ACTIONS + ("extend",)

    def take_action(self, action, dest, opt, value, values, parser):
        if action == "extend":
            values.ensure_value(dest, []).append(value)
        else:
            Option.take_action(
                self, action, dest, opt, value, values, parser)


def generate_options():
    """ Generate command line parser """
    usage_str = "usage: %prog <host> [options]"
    parser = OptionParser(usage=usage_str, option_class=MultipleOption)
    parser.add_option("-d", action="store_true",
                    dest="debug", help="Enable debug [default: %default]", default=False)

    parser.add_option("-f", action="store_true",
                    dest="search_files", help="search only for files [default: %default]", default=False)

    parser.add_option("-s", action="store_true",
                    dest="search_dirs", help="search only for subdirs [default: %default]", default=False)

    parser.add_option("-c", metavar="COOKIES", dest="cookie_file",
                    help="load cookies from file [default: %default]", default=None)

    parser.add_option("-a", action="store_true",
                    dest="download", help="Allow plugin to download files to 'output/' [default: %default]", default=False)

    parser.add_option("-b", action="store_true",
                    dest="recursive", help="Search for subdirs recursively [default: %default]", default=False)

    parser.add_option("-l", metavar="LIMIT", dest="limit",
                    help="limit recursive depth [default: %default]", default=conf.recursive_depth_limit)

    parser.add_option("-e", action="store_true",
                    dest="eval_output", help="Eval-able output [default: %default]", default=False)

    parser.add_option("-j", action="store_true",
                    dest="json_output", help="JSON output [default: %default]", default=False)

    parser.add_option("-m", metavar="MAXTIMEOUT", dest="max_timeout",
                    help="Max number of timeouts for a given request [default: %default]", default=conf.max_timeout_count)

    parser.add_option("-w", metavar="WORKERS", dest="workers", 
                    help="Number of worker threads [default: %default]", default=conf.thread_count)

    parser.add_option("-v", metavar="VHOST", dest="forge_vhost",
                    help="forge destination vhost [default: %default]", default='<host>')

    parser.add_option("-z", action="store_true",
                    dest="plugins_only", help="Only run plugins then exit [default: %default]", default=False)

    parser.add_option("-u", metavar="AGENT", dest="user_agent",
                    help="User-agent [default: %default]", default=conf.user_agent)

    parser.add_option("-p", metavar="PROXY", dest="proxy",
                    help="Use http proxy <scheme://url:port> [default: no proxy]", default='')

    parser.add_option("-x", "--plugin-configure",
                      action="extend", type="string",
                      dest="plugin_settings",
                      metavar="PLUGIN:OPTION_STRING",
                      default=[],
                      help="Plugin-specific configuration options.")

    return parser
    

def parse_args(parser, system_args):
    """ Parse and assign options """
    (options, args) = parser.parse_args(system_args)
    conf.debug = options.debug
    conf.max_timeout_count = int(options.max_timeout)
    conf.thread_count = int(options.workers)
    conf.user_agent = options.user_agent
    conf.cookies = load_cookie_file(options.cookie_file)
    conf.search_files = options.search_files
    conf.eval_output = options.eval_output
    conf.json_output = options.json_output
    conf.files_only = options.search_files
    conf.directories_only = options.search_dirs
    conf.recursive = options.recursive
    conf.recursive_depth_limit = int(options.limit)
    conf.forge_vhost = options.forge_vhost
    conf.plugins_only = options.plugins_only
    conf.allow_download = options.download
    conf.proxy_url = options.proxy

    for option in options.plugin_settings:
        plugin, value = option.split(':', 1)
        conf.plugin_settings[plugin].append(value)

    if conf.json_output:
        conf.eval_output = True

    return options, args


def load_cookie_file(afile):
    """
    Loads the supplied cookie file
    """
    if not afile:
        return None

    try:
        with open(afile, 'r') as cookie_file:
            content = cookie_file.read()
            content = content.replace('Cookie: ', '')
            content = content.replace('\n', '')
            return content
    except IOError:
        textutils.output_info('Supplied cookie file not found, will use server provided cookies')
        return None

