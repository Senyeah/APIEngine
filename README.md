# APIEngine (Beta)

[![Build Status](https://travis-ci.org/Senyeah/APIEngine.svg?branch=master)](https://travis-ci.org/Senyeah/APIEngine)

APIEngine allows you to easily create RESTful APIs using Apache and PHP with a simple endpoint definition language. It automatically routes requests to endpoints to classes defined inside your project.

While there are several frameworks which allow for the creation of RESTful APIs within PHP, most are bloated, cumbersome, and otherwise difficult to use. APIEngine attempts to solve all of those issues.

APIEngine is licensed under the GNU General Public License, version 3.

**APIEngine is currently in beta. If you find any bugs, please [submit an issue](https://github.com/Senyeah/APIEngine/issues/new)!** All feedback is appreciated.

## Server-Side Requirements

- PHP ≥ 5.5
- Apache 2 with `mod_rewrite` support enabled

## Client-Side Requirements

- Python 3

## Getting Started

Firstly, you’ll want to clone this repository locally—either by running `git clone https://github.com/Senyeah/APIEngine.git`, or by [downloading the zip directly](https://github.com/Senyeah/APIEngine/archive/master.zip).

Once you’ve downloaded the project and ensured that you have Python 3 installed, you’re ready to start using APIEngine.

### Your first endpoint

#### Defining the endpoints

You need to define what endpoints your API will provide, and where those requests should go when they are received. A simple definition file may be the following:

```
export GET "/info" to "InfoRequest" in "info.php"
```

In this example, we are `export`ing all `GET` requests your server receives to `/info` to the `InfoRequest` class inside `info.php`. You then invoke APIEngine on the client side, which generates the necessary folders and files, ready to be pushed to the server.

The definition file is passed as the standard input to the `apiengine create` command, using something like:

```
cat definition.txt | python3 apiengine create NewProject
```

This will then create a project called `NewProject`, in the current working directory, with the following directory structure:

```
NewProject
├── .htaccess
├── .definition
├── .definition.json
│
├── engine
│   ├── request.php
│   └──	runtime.php
│
└── info.php
```

Upon project creation, PHP source files and corresponding directories are automatically created which contain classes corresponding to what you defined inside your endpoint definition file.

#### Implementing the handler

Inside the `info.php` file, you will note that the `InfoRequest` class has been automatically generated. Inside the `execute` method of this class, you perform processing specific to that request and send a response.

In this case, we simply want to return information about our PHP configuration, so only a call to `phpinfo()` is necessary:

```php
require_once "engine/runtime.php";

class InfoRequest implements APIEngine\Requestable {
	public function execute($request) {
		phpinfo(); //Our code is inserted here
	}
}
```

#### Testing our endpoint

Once you have saved the code, direct Apache to have its root to the `NewProject` directory, before restarting it if necessary.

Then on a browser, visit `http://<your domain>/info` with your web browser (where `<your domain>` is the domain of your web browser—`localhost` if you’re running it locally).

Seeing the PHP information page indicates successful implementation of your endpoint.


## Endpoint Definition Syntax

The syntax to create endpoints was designed to be as simple and readable as possible. There are three main keywords which are used to control endpoint definition—`export`, `group`, and `base`.

### `export`

As its name suggests, the `export` directive “exports” a request to a specific class inside a specific PHP source file. Its syntax takes the following form:

```
export <http-method> "<endpoint>" to "<class-name>" in "<file-name>"
```

Where `<http-method>` is one of `GET`, `POST`, `PUT` or `DELETE`, and `<class-name>` is the name of the PHP class located inside `<file-name>`. 

`<endpoint>` is a URL to an API endpoint which is constructed of multiple _components_, each separated by forward slashes `/` (leading and trailing slashes are optional). Components can either be fixed strings (like `info`), variables, or optionals.

#### Variables

Variables allow for a component of the request to “vary”. The value passed then is obtained in the script by referencing the name you provide; variable names are enclosed in square brackets, like `[id]`. An example endpoint which uses variables may be:

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

This means that a browser would be able to send the following requests, both routed to the class `UserImageRequest` inside `users.php`:

```
/users/1234/image
/users/image
```

In the first case, `id` would have a value of `1234`. In the second case however, `id` would have a value of `null`.

### `base`

The `base` keyword allows you to set the base directory to where all files are relative to. Its syntax is fairly straightforward:

```
base "<directory>"
```

In the following example, the file `info.php` used in the `export` directive will be relative to the `code` directory (that is, `info.php` is located inside the `code` directory):

```
base "code"
export GET "/info" to "InfoRequest" in "info.php"
```

It can be set more than once, in which case it affects all directives beneath it (up until the next `base` directive):

```
base "users"
export GET "/" to "UserRequest" in "file.php"

base "misc/info"
export GET "/info" to "InfoRequest" in "file.php"
```

In this case, a GET request to `/` will route to `UserRequest` inside `users/file.php`, and a GET request to `/info` will route to `InfoRequest` inside `misc/info/file.php`.

### `group`

The `group` keyword allows similar endpoints to be grouped together in order to increase readability. A `group` directive has the following format:

```
group "<common-endpoint>" (base "<directory>")?
	(<export-directive>)+
```

Where `<common-endpoint>` is an endpoint shared by each endpoint in the group, and `<export-directive>` is an export directive where the URL is relative to `<common-endpoint>`.

An example of using `group` may be something like:

```
group "/users/[id]?" base "users"
	export GET "/" to "UserGetRequest" in "main.php"
	export PUT "/" to "UserUpdateRequest" in "main.php"
	export DELETE "/" to "UserDeleteRequest" in "main.php"
	export GET "/image/[size]?" to "UserImageGetRequest" in "image.php"
```

In this case:

- A GET, PUT or DELETE request to `/users` or `/users/<some id>` will route to `User(Get|Update|Delete)Request` inside `users/main.php`
- A GET request to `/users/image`, `/users/<some id>/image`, `/users/image/<some size>`, or `/users/<some id>/image/<some size>` will route to `UserImageGetRequest` inside `users/image.php`.

A base directory can optionally be specified for the group in addition to any root `base` directives. In the case where both are present, the group base directory is appended to the root base directory. An example of using this may be:

```
base "users"

group "/users/image" base "images"
	export GET "/" to "UserImageGetRequest" in "main.php"
	export POST "/" to "UserImageCreateRequest" in "main.php"
```

In this case:

- A GET request to `/users/image` will route to `UserImageGetRequest` inside `users/images/main.php`
- A POST request to `/users/image` will route to `UserImageCreateRequest` inside `users/images/main.php`

## Request Handler Classes inside PHP

Each class which you define for endpoints to be routed to must implement the `Requestable` interface. The interface requires a single method to be implemented, and is defined as follows:

```php
interface Requestable {
	public function execute($request);	
}
```

This method passes a `Request` object as its argument to the call. `Request` is defined as the following class:

```php
class Request {
	public $method;
	public $arguments;
	public $headers;
}
```

| Property |        Type         | Description |
| -------- | ------------------- | ----------- |
| `method` | `string` | The request method used when the endpoint was called. Its value will be one of `Method::GET`, `Method::POST`, `Method::PUT`, or `Method::DELETE`. |
| `arguments` | `array` | The arguments passed to the script, if there were any. Where arguments exist, the name of the key corresponds to the name of the variable inside the endpoint definition language. |
| `headers` | `array` | The request headers sent to Apache. This field is assigned by calling the `apache_request_headers` function. |

### Notes

- All classes and interfaces are located inside the `APIRequest` namespace. 

- It’s the responsibility of the class itself to return appropriate responses itself, for example using calls to `header` and by invoking `echo`.

- If you attempt to route an endpoint to a class which either doesn’t exist or does not implement the `Requestable` interface, an exception will result and a `500 Internal Server Error` response will be sent back to the requester.

## Interfacing with APIEngine

### Creating a project

In order to create a project, you can invoke APIEngine like so:

```
cat <definition file> | python3 apiengine create <path to your new project>
```

APIEngine will then initialise a new project located at `<path to your new project>`, relative to the current working directory. The endpoint definition file is given as the standard input.

If `<path to your new project>` is not given, a new project named `Untitled` is created in the current working directory.

### Updating a project

To update the endpoint definition file after the project has been created, you need to edit the `.definition` file in the project’s root directory. To actually reflect these changes you need to tell APIEngine to recompile the file:

```
sudo python3 apiengine update <path to your project>
```

It’s important to use `sudo` here, as the endpoint definition file was initially created with permissions `r--r-----` (that is, it cannot be written to without superuser permissions).

### Deleting a project

To delete a project, use the following command:

```
sudo python3 apiengine remove <path to your project>
```

This is essentially the same as issuing `sudo rm -r <path to your project>`, except it ensures that directory is actually a valid project prior to removal.

## Important Notes

- In order to avoid ambiguity between variable names, you can’t place optional variables consecutively in an endpoint definition:

  ```
  /users/[id]?/[size]?/image
  ```  

  This is because in the case where a request like `/users/1234/image` is sent, it’s impossible to tell whether to place `1234` inside `id` or `size`. If you attempt to do this, an exception will be thrown as your endpoint definition file is parsed.  
  
- Keywords (`export`, `base`, `GET`…) are case-sensitive

- Single quotes (`'`) are not supported—double quotes (`"`) must be used instead, as in the above examples

- You cannot have endpoints pointing to `engine/runtime.php` or `engine/request.php`, as these files are used at runtime by APIEngine.

- All file paths are relative to the project’s root directory—that is `/file` is the same as just `file`

- The `.htaccess` file which is automatically generated provides URL rewriting to redirect all requests to `engine/request.php`. If you have any custom directives to place inside the `.htaccess` file, ensure that you do not change the contents of the URL rewriting section.

- Upon project creation, the endpoint definition file passed through `stdin` is written to the `.definition.json` file, located in the project’s root directory. For security, this file has permissions `r--r-----` (0440). When pushing your API to a server, always ensure the permissions of this file has not changed, and that it is owned by your web server’s user (typically `www-data` on Linux).

- All files and folders are automatically generated with appropriate classes upon project creation, but it’s your responsibility to ensure they exist upon a project update.