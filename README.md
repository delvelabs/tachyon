[![Build Status](https://travis-ci.org/delvelabs/tachyon.svg?branch=master)](https://travis-ci.org/delvelabs/tachyon)
[![PyPi](https://badge.fury.io/py/tachyon3.svg)](https://badge.fury.io/py/tachyon3)

# Tachyon

Tachyon is a fast web application security reconnaissance tool.

It is specifically meant to crawl a web application and look for left over or non-indexed files with the addition of reporting pages or scripts leaking internal data.

## User Requirements    

- Linux
- Python 3.6+

## User Installation

### Install:

```bash
$ mkdir tachyon
$ python3 -m venv tachyon/
$ cd tachyon
$ source bin/activate
$ pip install tachyon3
$ tachyon -h
```
### Upgrading:

```bash
$ cd tachyon
$ source bin/activate
$ pip install --ignore-installed --upgrade tachyon3
```

### Usage:

```bash
$ cd tachyon
$ source bin/activate
$ tachyon -h
```

## Developers Installation

```bash
$ git clone https://github.com/delvelabs/tachyon.git
$ mkdir tachyon
$ python3 -m venv tachyon/
$ source tachyon/bin/activate
$ cd tachyon
$ pip install -r requirements-dev.txt
```

## Getting started

Note: if you have the source code version, replace ```tachyon``` with ```python3 -m tachyon``` in the examples below.

```bash
$ cd tachyon
$ source bin/activate
```

To run a discovery with the default settings:
```bash
tachyon http://example.com/
```

To run a discovery over a proxy:
```bash
tachyon -p http://127.0.0.1:8080 http://example.com/
```

To search for files only:
```bash
tachyon -f http://example.com/
```

To search for directories only:
```bash
tachyon -s http://example.com/
```

To output results to JSON format:
```bash
tachyon -j http://example.com/
```

## command line options

```
Usage: __main__.py [OPTIONS] TARGET_HOST

Options:
  -a, --allow-download
  -c, --cookie-file TEXT
  -l, --depth-limit INTEGER
  -s, --directories-only
  -f, --files-only
  -j, --json-output
  -m, --max-retry-count INTEGER
  -z, --plugins-only
  -x, --plugin-settings TEXT
  -p, --proxy TEXT
  -r, --recursive
  -u, --user-agent TEXT
  -v, --vhost TEXT
  -C, --confirmation-factor INTEGER
  --har-output-dir TEXT
  -h, --help                      Show this message and exit.
```

### Format for the cookies file

```
cookie0=value0;
cookie1=value1;
cookie2=value2;
```

## Plugins

### Existing plugins:

* HostProcessor: This plugin processes the hostname to generate hosts and filenames relatives to it.
* PathGenerator: Generate simple paths with letters and digits (ex: /0).
* Robots: Add the paths in robots.txt to the paths database.
* SitemapXML: Add paths and files found in the site map to the database.
* Svn: Fetch /.svn/entries and parse for target paths.

### Plugins settings

Settings can be passed to the plugins via the ``-x`` option. Each option is a key/value pair, with a colon joining the key
 and its value. Use a new ``-x`` for each setting.
 
```bash
tachyon -x setting0:value0 -x setting1:value1 -x setting2:value2 http://example.com/
```

## Contributing

Most contributions are welcome. Simply submit a pull request on [GitHub](https://github.com/delvelabs/tachyon/).

Instruction for contributors:
* Accept the contributor license agreement.
* Write tests for your code. Untested code will be rejected.

To report a bug or suggest a feature, open an issue.

## License

Copyright 2019- Delve Labs inc.

This software is published under the GNU General Public License, version 2.
