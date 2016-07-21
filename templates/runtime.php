<?php

namespace APIEngine;

class Request {
    public $method;
    public $arguments;
    public $headers;
}

class Method {
	const GET = "GET";
    const POST = "POST";
    const DELETE = "DELETE";
    const PUT = "PUT";
}

interface Requestable {
    public function execute($request);  
}
	
?>