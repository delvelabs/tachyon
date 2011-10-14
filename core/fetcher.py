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
import socket
import ssl
import random
from core import database
from _socket import timeout
from urllib2 import URLError, HTTPError, HTTPHandler, HTTPSHandler
from urllib2 import ProxyHandler, build_opener, HTTPRedirectHandler, HTTPDefaultErrorHandler
from httplib import BadStatusLine, HTTPConnection, HTTPSConnection
from core import conf, utils
from urlparse import urlparse
from threading import Lock

def get_random_ip_from_cache(cache_info):
    """ Get a random ip from the caches entries """
    random_entry = cache_info[random.randint(0, len(cache_info) - 1)]
    host_port = random_entry[4]
    return host_port[0] 

def resolve_cached(host, port):
    """ Fetch the resolved ip addresses from the cache and return a random address if load-balanced """
    resolved = database.dns_cache.get(host)
    if not resolved:
        lock = Lock()
        lock.acquire()
        utils.output_debug("Host entry not found in cache for host:" + str(host) + ", resolving")
        resolved = socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM)
        database.dns_cache[host] = resolved
        lock.release()
    
    return get_random_ip_from_cache(resolved), port    
        

class TachyonHTTPConnection(HTTPConnection):
    def connect(self):
        self.sock = socket.create_connection(resolve_cached(self.host,self.port),self.timeout)
    
class TachyonHTTPSConnection(HTTPSConnection):
    def connect(self):
        sock = socket.create_connection(resolve_cached(self.host,self.port), self.timeout)
        self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file)

class TachyonHTTPHandler(HTTPHandler):
    def http_open(self,req):
        return self.do_open(TachyonHTTPConnection,req)

class TachyonHTTPSHandler(HTTPSHandler):
    def https_open(self,req):
        return self.do_open(TachyonHTTPSConnection,req)


class SmartRedirectHandler(HTTPRedirectHandler):    
    """ Handle various bogus redirects """ 
    
    def detect_real_response(self, code, request, headers):
        """ 
            This function detects if we are subjected to an invalid redirect
            If we try to hit /test/file.ext and the server issues a redirect for
            /404 or /rewritten_path, we know that we didn't hit a flat file.
            
            It also detects common redirect such as /test -> /test/ (valid)
            
            return the response code if the redirect is valid and 404 if not
        """
        location = headers.get('location')
        if location:
            parsed_target = urlparse(request.get_full_url())
            parsed_redirect = urlparse(location)
            
            # Simple 401 redirect ON A PATH, www.host.com/folder -> www.host.com/folder/, don't follow redirect.         
            if parsed_target.path + '/' == parsed_redirect.path:
                utils.output_debug("Hit directory " + str(code) + " with valid redirect from: " + request.get_full_url() + " to: " + str(location)) 
                return 200       
            
            # Redirected to some other location but with same file target (likely a load balancer proxy)
            # host.com/folder/ -> www.host.com/folder/
            # Follow this redirect
            if parsed_target.path in parsed_redirect.path:
                utils.output_debug("Hit " + str(code) + " with valid redirect from: " + request.get_full_url() + " to: " + str(location)) 
                return code           
            
            # Else, it's a bogus redirect
            utils.output_debug("Hit " + str(code) + " with invalid redirect from: " + request.get_full_url()) 
            return 404    

        
    def http_error_301(self, req, fp, code, msg, headers):  
        """ Handle 301 response code """
        real_code = self.detect_real_response(code, req, headers)
        if code != real_code:
            return HTTPDefaultErrorHandler.http_error_default(HTTPDefaultErrorHandler(), req, fp, real_code, msg, headers)
        else:
            return HTTPRedirectHandler.http_error_301(self, req, fp, code, msg, headers)                                           


    def http_error_302(self, req, fp, code, msg, headers):   
        """ Handle 302 response code """
        real_code = self.detect_real_response(code, req, headers)
        if code != real_code:
            return HTTPDefaultErrorHandler.http_error_default(HTTPDefaultErrorHandler(), req, fp, real_code, msg, headers)
        else:
            return HTTPRedirectHandler.http_error_301(self, req, fp, code, msg, headers)    
        
        
    def http_error_303(self, req, fp, code, msg, headers):  
        """ Handle 303 response code """
        real_code = self.detect_real_response(code, req, headers)
        if code != real_code:
            return HTTPDefaultErrorHandler.http_error_default(HTTPDefaultErrorHandler(), req, fp, real_code, msg, headers)
        else:
            return HTTPRedirectHandler.http_error_301(self, req, fp, code, msg, headers)    


    def http_error_307(self, req, fp, code, msg, headers):
        """ Handle 307 response code """   
        real_code = self.detect_real_response(code, req, headers)
        if code != real_code:
            return HTTPDefaultErrorHandler.http_error_default(HTTPDefaultErrorHandler(), req, fp, real_code, msg, headers)
        else:
            return HTTPRedirectHandler.http_error_301(self, req, fp, code, msg, headers)    
             


class Fetcher(object):
    def read_content(self, response, limit_len=True):
        """ Reads the content from the response and build a string with it """
        try:
            if limit_len:
                content = response.read(conf.crc_sample_len)
            else:
                content = ''
                while True:
                    tmp = response.read(1024)
                    if tmp == '':
                        break
                    else:
                        content = content + tmp
        except timeout:
            raise timeout
        else:
            return content    


    def fetch_url(self, url, user_agent, timeout, limit_len=True):
        """ Fetch a given url, with a given user_agent and timeout"""
        try:
            redirect_handler = SmartRedirectHandler()

            if conf.use_tor:
                proxy_support = ProxyHandler({'http': 'http://localhost:8118'})
                opener = build_opener(TachyonHTTPHandler, TachyonHTTPSHandler, proxy_support, redirect_handler)
            else:
                opener = build_opener(TachyonHTTPHandler, TachyonHTTPSHandler, redirect_handler)

            socket.setdefaulttimeout(timeout)
            opener.addheaders = [('User-Agent', user_agent)]    
            response = opener.open(url, timeout=timeout)
            
            content = self.read_content(response, limit_len)
            code = response.code
            headers = dict(response.headers)
            response.close()
        except HTTPError as httpe:
            code = httpe.code
            content = ''
            headers = dict(httpe.headers)
        except (URLError, BadStatusLine, timeout):
            code = 0
            content = ''
            headers = dict()
            
            
        return code, content, headers
