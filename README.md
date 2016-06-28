# Introduction

Tachyon is a Fast Multi-Threaded Web Discovery Tool.

The main goal of tachyon is to help webadmins find leftover files in their
site installation, permission problems and web server configuration errors.

It is not a vulnerability scanner, or a web crawler.

# Features

It provides:
 - Plugin support
 - SSL support
 - Robots.txt support
 - Common directory lookup
 - Fast Multi-Threaded execution
 - Automatic variable rate limiter
 - Recursive scanning

# Requirements    

- A mainstream OS (Windows, Linux, Mac OS X)
- Python 3.x (Could still work with 2.7, with minor issues)
- urllib3 1.1+

```
pip install -r requirements.txt
```

# How to help (for sysadmins)

- Run tachyon on your domain
- Run a recursive directory listing of your domain (I don't need to know what the domain is)
- Send me the result list and the directory listing

# Known bugs

- String matching is not working properly for now, response data is somewhat truncated. File will still be reported but without content matching validation.

Possible future improvements:
- Put back TOR support.
- Parseable output for GUI integration (better stats system for live stats)
- Add an `match-string=404` mechanism for edge cases
- Add callbacks method to plugins
- Support files in robots plugin
- Add support for non-xml `/.svn/entries` files
- `Sitemap.xml` plugin

