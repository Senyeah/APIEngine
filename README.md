# APIEngine

Status: ![Build Status](https://travis-ci.org/Senyeah/APIEngine.svg?branch=master)

APIEngine allows you to easily create RESTful APIs using Apache and PHP with a simple endpoint definition language. It automatically routes requests to endpoints to classes defined inside your project.

While there are a few frameworks which allow for the creation of RESTful APIs within PHP, most are bloated, cumbersome, and otherwise difficult to use. APIEngine attempts to solve all of those issues.

APIEngine is licensed under the GNU General Public License, version 3.

## Server-Side Requirements

- PHP ≥ 5.5
- Apache 2 with `mod_rewrite` support enabled

## Client-Side Requirements

- Python 3

## Getting Started

In order to begin, you need to define what endpoints your API will provide and where those requests should go when they are received. A simple definition file may be the following:

```
export GET "/info" to "InfoRequest" in "info.php"
```

In this example, we are `export`ing all `GET` requests to the `InfoRequest` class inside `info.php`. You then invoke APIEngine on the client side, which generates the necessary folders and files, ready to be pushed to the server.

The definition file is passed as the standard input to the `apiengine create` command:

```cat definition.txt | python3 apiengine.py create```

This will then create a project called `Untitled`, in the current working directory, with the following directory structure:

```
Untitled
│	.htaccess
│	.definition
│
├─── endpoints
│	 └─ info.php
│
└─── request.php
```

The `.htaccess` file which is generated provides URL rewriting to redirect all requests to `request.php`, located in the project’s root directory. If you have any custom directives to place inside the `.htaccess` file, ensure you do not change the contents of the URL rewriting section.

The endpoint definition file passed in as the standard input is directed to the `.definition` file, and has permissions `r--------` (0400) in order to ensure that it can only be modified by authorised parties. When pushing your API to a server, always ensure the permission of this file has not changed.

The `endpoints` directory contains the main “body” of your API. Upon creation, files are automatically created which contain PHP classes corresponding to what you defined inside your endpoint definition file.