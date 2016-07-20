# APIEngine

![Build Status](https://travis-ci.org/Senyeah/APIEngine.svg?branch=master)

APIEngine allows you to easily create RESTful APIs using Apache and PHP with a simple endpoint definition language. It automatically routes requests to endpoints to classes defined inside your project.

While there are a few frameworks which allow for the creation of RESTful APIs within PHP, most are bloated, cumbersome, and otherwise difficult to use. APIEngine attempts to solve all of those issues.

APIEngine is licensed under the GNU General Public License, version 3.

## Server-Side Requirements

- PHP ≥ 5.5
- Apache 2 with `mod_rewrite` support enabled

## Client-Side Requirements

- Python 3

## Getting Started

You need to define what endpoints your API will provide, and where those requests should go when they are received. A simple definition file may be the following:

```
export GET "/info" to "InfoRequest" in "info.php"
```

In this example, we are `export`ing all `GET` requests to the `InfoRequest` class inside `info.php`. You then invoke APIEngine on the client side, which generates the necessary folders and files, ready to be pushed to the server.

The definition file is passed as the standard input to the `apiengine create` command:

```cat definition.txt | python3 apiengine.py create```

This will then create a project called `Untitled`, in the current working directory, with the following directory structure:

```
Untitled
├── .htaccess
├── .definition
│
├── info.php
└── request.php
```

The `.htaccess` file which is generated provides URL rewriting to redirect all requests to `request.php`, located in the project’s root directory. If you have any custom directives to place inside the `.htaccess` file, ensure you do not change the contents of the URL rewriting section.

The endpoint definition file passed in as the standard input is written to the `.definition` file, located in the project’s root directory. This file has permissions `r--------` (0400) in order to ensure that it can only be modified by authorised parties. When pushing your API to a server, always ensure the permission of this file has not changed.

Upon project creation, PHP source files are automatically created which contain classes corresponding to what you defined inside your endpoint definition file.

## Endpoint Definition Syntax

The syntax to create endpoints was designed to be as simple and readable as possible. There are three main keywords which are used to control endpoint definition:

### `export`

As its name suggests, `export` exports a request to a specific class inside a specific PHP source file. Its syntax is as follows:

```
export <http-method> "<endpoint>" to "<class-name>" in "<file-name>"
```

Where `<http-method>` is one of `GET`, `POST`, `PUT` or `DELETE`, `<class-name>` is the name of the PHP class located inside `<file-name>`. 

`<endpoint>` is a URL to an API endpoint which is constructed of multiple _components_, separated by forward slashes `/`. Components can either be fixed strings (like `info`), variables, or optionals.

#### Variables

Variables allow for that part of a component to be anything whatsoever, and the value can be obtained in the script by referencing the name you provide inside the component. Variable names are enclosed in square brackets, like `[id]`. An example endpoint which uses variables may be:

```
export GET "/users/[id]/image" to "UserImageRequest" in "users.php"
```

If a browser sends the following GET request to the server:

```
/users/1234/image
```

This request will be routed to `UserImageRequest` inside `users.php`, with the value of `id` being `1234`.

#### Optionals

Optionals are variables which may optionally be omitted when requesting an endpoint. As with variables, their name is encased in square brackets, except with a trailing `?`:

```
export GET "/users/[id]?/image" to "UserImageRequest" in "users.php"
```

This means that a browser would be able to send the following requests, both routed to `UserImageRequest` inside `users.php`:

```
/users/1234/image
/users/image
```

In the first case—like before—`id` would have a value of `1234`. In the second case however, it would have a value of `null`.

## Miscellaneous

- In order to avoid ambiguity between optional types, you can’t have two optional variables consecutively in an endpoint definition, like in the following example:  

  ```
  /users/[id]?/[size]?/image
  ```  

  This is because in the case where a request like `/users/1234/image` is sent, it’s impossible to tell whether to place `1234` inside `id` or `size`. If you attempt to do this, an exception will be thrown when your endpoint definition file is being parsed.  


All files are automatically generated with appropriate classes upon project creation, but it’s your responsibility to ensure they exist upon a project update.