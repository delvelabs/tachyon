# Tachyon - Fast Multi-Threaded Web Discovery Tool
# Copyright (c) 2011 Gabriel Tremblay - initnull hat gmail.com
#
#
# Copyright (c) 2001-2010 Python Software Foundation; All Rights Reserved
# Based on python urllib2
# Changes : Added host forgery in http headers
#
# This file is licensed under the PSF License, which is GPL-Compatible
# http://docs.python.org/license.html
#

from core import conf
from urllib import unwrap, unquote, splittype, splithost, splittag
from urllib2 import ProxyHandler, UnknownHandler, HTTPHandler, HTTPDefaultErrorHandler
from urllib2 import HTTPRedirectHandler, FileHandler, FTPHandler, HTTPErrorProcessor, HTTPSHandler
import bisect
import httplib
import re
import socket
import urlparse

# copied from cookielib.py
_cut_port_re = re.compile(r":\d+$")
def request_host(request):
    """Return request-host, as defined by RFC 2965.

    Variation from RFC: returned value is lowercased, for convenient
    comparison.

    """
    url = request.get_full_url()
    host = urlparse.urlparse(url)[1]
    if host == "":
        host = request.get_header("Host", "")

    # remove port, if present
    host = _cut_port_re.sub("", host, 1)
    return host.lower()

class Request:

    def __init__(self, url, data=None, headers=dict(),
                 origin_req_host=None, unverifiable=False):
        # unwrap('<URL:type://host/path>') --> 'type://host/path'
        self.__original = unwrap(url)
        self.__original, fragment = splittag(self.__original)
        self.type = None
        # self.__r_type is what's left after doing the splittype
        self.host = None
        self.port = None
        self._tunnel_host = None
        self.data = data
        self.headers = {}
        for key, value in headers.items():
            self.add_header(key, value)
        self.unredirected_hdrs = {}
        if origin_req_host is None:
            origin_req_host = request_host(self)
        self.origin_req_host = origin_req_host
        self.unverifiable = unverifiable

    def __getattr__(self, attr):
        # XXX this is a fallback mechanism to guard against these
        # methods getting called in a non-standard order.  this may be
        # too complicated and/or unnecessary.
        # XXX should the __r_XXX attributes be public?
        if attr[:12] == '_Request__r_':
            name = attr[12:]
            if hasattr(Request, 'get_' + name):
                getattr(self, 'get_' + name)()
                return getattr(self, attr)
        raise AttributeError, attr

    def get_method(self):
        if self.has_data():
            return "POST"
        else:
            return "GET"

    # XXX these helper methods are lame

    def add_data(self, data):
        self.data = data

    def has_data(self):
        return self.data is not None

    def get_data(self):
        return self.data

    def get_full_url(self):
        return self.__original

    def get_type(self):
        if self.type is None:
            self.type, self.__r_type = splittype(self.__original)
            if self.type is None:
                raise ValueError, "unknown url type: %s" % self.__original
        return self.type

    def get_host(self):
        if self.host is None:
            self.host, self.__r_host = splithost(self.__r_type)
            if self.host:
                self.host = unquote(self.host)
        return self.host

    def get_selector(self):
        return self.__r_host

    def set_proxy(self, host, type):
        if self.type == 'https' and not self._tunnel_host:
            self._tunnel_host = self.host
        else:
            self.type = type
            self.__r_host = self.__original

        self.host = host

    def has_proxy(self):
        return self.__r_host == self.__original

    def get_origin_req_host(self):
        return self.origin_req_host

    def is_unverifiable(self):
        return self.unverifiable

    def add_header(self, key, val):
        # useful for something like authentication
        self.headers[key.capitalize()] = val

    def add_unredirected_header(self, key, val):
        # will not be added to a redirected request
        self.unredirected_hdrs[key.capitalize()] = val

    def has_header(self, header_name):
        return (header_name in self.headers or
                header_name in self.unredirected_hdrs)

    def get_header(self, header_name, default=None):
        return self.headers.get(
            header_name,
            self.unredirected_hdrs.get(header_name, default))

    def header_items(self):
        hdrs = self.unredirected_hdrs.copy()
        hdrs.update(self.headers)
        return hdrs.items()

class OpenerDirector:
    def __init__(self):
        client_version = "Python-urllib2-forgery/%s" % conf.version
        self.addheaders = [('User-agent', client_version)]
        # manage the individual handlers
        self.handlers = []
        self.handle_open = {}
        self.handle_error = {}
        self.process_response = {}
        self.process_request = {}

    def add_handler(self, handler):
        if not hasattr(handler, "add_parent"):
            raise TypeError("expected BaseHandler instance, got %r" %
                            type(handler))

        added = False
        for meth in dir(handler):
            if meth in ["redirect_request", "do_open", "proxy_open"]:
                # oops, coincidental match
                continue

            i = meth.find("_")
            protocol = meth[:i]
            condition = meth[i+1:]

            if condition.startswith("error"):
                j = condition.find("_") + i + 1
                kind = meth[j+1:]
                try:
                    kind = int(kind)
                except ValueError:
                    pass
                lookup = self.handle_error.get(protocol, {})
                self.handle_error[protocol] = lookup
            elif condition == "open":
                kind = protocol
                lookup = self.handle_open
            elif condition == "response":
                kind = protocol
                lookup = self.process_response
            elif condition == "request":
                kind = protocol
                lookup = self.process_request
            else:
                continue

            handlers = lookup.setdefault(kind, [])
            if handlers:
                bisect.insort(handlers, handler)
            else:
                handlers.append(handler)
            added = True

        if added:
            # the handlers must work in an specific order, the order
            # is specified in a Handler attribute
            bisect.insort(self.handlers, handler)
            handler.add_parent(self)

    def close(self):
        # Only exists for backwards compatibility.
        pass

    def _call_chain(self, chain, kind, meth_name, *args):
        # Handlers raise an exception if no one else should try to handle
        # the request, or return None if they can't but another handler
        # could.  Otherwise, they return the response.
        handlers = chain.get(kind, ())
        for handler in handlers:
            func = getattr(handler, meth_name)

            result = func(*args)
            if result is not None:
                return result

    def open(self, fullurl, data=None, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, headers=dict()):
        # accept a URL or a Request object
        if isinstance(fullurl, basestring):
            req = Request(fullurl, data, headers=headers)
        else:
            req = fullurl
            if data is not None:
                req.add_data(data)

        req.timeout = timeout
        protocol = req.get_type()

        # pre-process request
        meth_name = protocol+"_request"
        for processor in self.process_request.get(protocol, []):
            meth = getattr(processor, meth_name)
            req = meth(req)

        response = self._open(req, data)

        # post-process response
        meth_name = protocol+"_response"
        for processor in self.process_response.get(protocol, []):
            meth = getattr(processor, meth_name)
            response = meth(req, response)

        return response

    def _open(self, req, data=None):
        result = self._call_chain(self.handle_open, 'default',
                                  'default_open', req)
        if result:
            return result

        protocol = req.get_type()
        result = self._call_chain(self.handle_open, protocol, protocol +
                                  '_open', req)
        if result:
            return result

        return self._call_chain(self.handle_open, 'unknown',
                                'unknown_open', req)

    def error(self, proto, *args):
        orig_args = list()
        if proto in ('http', 'https'):
            # XXX http[s] protocols are special-cased
            dict = self.handle_error['http'] # https is not different than http
            proto = args[2]  # YUCK!
            meth_name = 'http_error_%s' % proto
            http_err = 1
            orig_args = args
        else:
            dict = self.handle_error
            meth_name = proto + '_error'
            http_err = 0
        args = (dict, proto, meth_name) + args
        result = self._call_chain(*args)
        if result:
            return result

        if http_err:
            args = (dict, 'default', 'http_error_default') + orig_args
            return self._call_chain(*args)

def build_opener(*handlers):
    """Create an opener object from a list of handlers.

    The opener will use several default handlers, including support
    for HTTP, FTP and when applicable, HTTPS.

    If any of the handlers passed as arguments are subclasses of the
    default handlers, the default handlers will not be used.
    """
    import types
    def isclass(obj):
        return isinstance(obj, (types.ClassType, type))

    opener = OpenerDirector()
    default_classes = [ProxyHandler, UnknownHandler, HTTPHandler,
                       HTTPDefaultErrorHandler, HTTPRedirectHandler,
                       FTPHandler, FileHandler, HTTPErrorProcessor]
    if hasattr(httplib, 'HTTPS'):
        default_classes.append(HTTPSHandler)
    skip = set()
    for klass in default_classes:
        for check in handlers:
            if isclass(check):
                if issubclass(check, klass):
                    skip.add(klass)
            elif isinstance(check, klass):
                skip.add(klass)
    for klass in skip:
        default_classes.remove(klass)

    for klass in default_classes:
        opener.add_handler(klass())

    for h in handlers:
        if isclass(h):
            h = h()
        opener.add_handler(h)
    return opener
  