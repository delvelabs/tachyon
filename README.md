# Tachyon

Tachyon is a fast web application security reconnaissance tool.

It is specifically meant to crawl web application and look for left over or non-indexed files with the addition of reporting pages or scripts leaking internal data.

## User Requirements    

- Linux
- Python 3.5.2

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
$ cd tachyon
$ source bin/activate
$ tachyon -h

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

* ```a, --allow-download``` allow plugins supporting the feature to download files they fetch.
* ```c, --cookie-file``` Path to a file containing the cookies to use for the discovery. Format is described 
                         [here](#format-for-the-cookies-file).
* ```l, --depth-limit``` Maximum depth for recursive search of directories, default is 2.
* ```s, --directories-only``` Only search for directories. Can not be used with -f.
* ```f, --files-only``` Only search for files. Can not be used with -s.
* ```j, --json-output``` Output the results in JSON format.
* ```m, --max-retry-count``` The amount of times a failed request will be retried before being dropped. Default is 3.
* ```z, --plugins-only``` Only execute plugins.
* ```x, --plugin-settings``` Settings to pass to the plugins. Read [this section](#plugins-settings) for more details.
* ```p, --proxy``` URL of the proxy to use for discovery.
* ```r, --recursive``` perform a recursive directory search. Use -l to limit the depth of the search.
* ```u, --user-agent``` User agent to put in the headers of the requests made by Tachyon. Default is 'Mozilla/5.0 
    (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36'.
* ```v, --vhost``` Address of the virtual host if the target of the discovery is a hidden virtual host.

### Format for the cookies file

```
cookie0=value0;
cookie1=value1;
cookie2=value2;
```

## Plugins

### Existing plugins:

* HostProcessor: This plugin process the hostname to generate host and filenames relatives to it.
* PathGenerator: Generate simple paths with letters and digits (ex: /0).
* Robots: Add the paths in robots.txt to the paths database.
* SitemapXML: Add paths and files found in the site map to the database.
* Svn: Fetch /.svn/entries and parse for target paths.

### Plugins settings

Settings can be pass to the plugins via the ``-x`` option. Each option is a key/value pair, with a colon joining the key
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

Copyright 2018- Delve Labs inc.

This software is published under the GNU General Public License, version 2.
