# Tachyon

## Introduction

Tachyon is a fast Web discovery tool.

The main goal of tachyon is to help webadmins find leftover files in their
site installation, permission problems and web server configuration errors.

It is not a vulnerability scanner, nor a web crawler.

## Features

It provides:
 - Plugin support
 - SSL support
 - Robots.txt support
 - Common directory lookup
 - Recursive scanning

## Requirements    

- Linux
- Python 3.5.2

## Installation

### Pip version:

```bash
pip install git+https://github.com/delvelabs/tachyon.git
```

### Source code version

```bash
git clone https://github.com/delvelabs/tachyon.git
cd tachyon
pip install -r requirements.txt
```

## Getting started

Note: if you have the source code version, replace ```tachyon``` with ```python -m tachyon``` in the examples below.

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
* ```c, --cookie-file``` Path to a file containing the cookies to use for the discovery.
* ```l, --depth-limit``` Maximum depth for recursive search of directories, default is 2.
* ```s, --directories-only``` Only search for directories. Can not be used with -f.
* ```f, --files-only``` Only search for files. Can not be used with -s.
* ```j, --json-output``` Output the results in JSON format.
* ```m, --max-retry-count``` The amount of times a failed request will be retried before being dropped. Default is 3.
* ```z, --plugins-only``` Only execute plugins.
* ```x, --plugin-settings``` Settings to pass to the plugins.
* ```p, --proxy``` URL of the proxy to use for discovery.
* ```r, --recursive``` perform a recursive directory search. Use -l to limit the depth of the search.
* ```u, --user-agent``` User agent to put in the headers of the requests made by Tachyon. Default is 'Mozilla/5.0 
    (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36'.
* ```v, --vhost``` Address of the virtual host if the target of the discovery is a hidden virtual host.
