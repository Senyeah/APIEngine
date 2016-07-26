<?php

require_once "runtime.php";

use APIEngine\Method;

abstract class EndpointComponent {
	const WILDCARD = "*";
	const ROOT = "/";
}

class RedirectEntry {
	
	public $class_name;
	public $file_name;
	public $parameters;
	
	function __construct($dict) {
		$this->class_name = $dict["class"];
		$this->file_name = $dict["file"];
		$this->parameters = array_key_exists("parameters", $dict) ? $dict["parameters"] : [];
	}
	
}

class APIRequest {
	
	private $method;
	private $arguments;
	
	private $redirect_tree;
	
	static function internal_error($reason) {
		
		$decorated_reason = "APIEngine: Error: $reason";
		error_log($decorated_reason);
			
		header("HTTP/1.1 500 Internal Server Error");
		die("<h1>500 Internal Server Error</h1><p>$decorated_reason</p>");
		
	}
	
	private function redirect_entry_for_request($method, $components) {

		if (is_null($this->redirect_tree) || !array_key_exists($method, $this->redirect_tree)) {
			return null;
		}
		
		$sub_tree = $this->redirect_tree[$method];
		$current_item = 0;
		
		while ($current_item < count($components)) {
			$current_component = $components[$current_item];
			
			if (array_key_exists($current_component, $sub_tree)) {
				$sub_tree = $sub_tree[$current_component];
				$current_item++;
			} else if (array_key_exists(EndpointComponent::WILDCARD, $sub_tree)) {
				$sub_tree = $sub_tree[EndpointComponent::WILDCARD];
				$current_item++;
			} else if (count($current_component) == 0) {
				break;
			} else {
				return null;
			}
		}
		
		if (array_key_exists(EndpointComponent::ROOT, $sub_tree)) {
			return new RedirectEntry($sub_tree[EndpointComponent::ROOT]);
		} else {
			return null;
		}
		
	}
	
	function execute() {
		
		$desired_entry = $this->redirect_entry_for_request($this->method, $this->arguments);
        
        if (is_null($desired_entry)) {
	        header("HTTP/1.1 404 Not Found");
	        die("<h1>404 Not Found</h1><p>The requested endpoint ‘/" . $_REQUEST["arguments"] . "’ does not exist</p>");
        }

		//We can now construct the request object
        
        $request = new APIEngine\Request();
        
        $request->method = $this->method;
        $request->headers = apache_request_headers();
        $request->arguments = [];
        
        //Get the arguments and map them to their names
        
        foreach ($desired_entry->parameters as $index => $name) {
	        $request->arguments[$name] = $this->arguments[$index];
        }
        
        //Now we open the desired class and ensure that it implements the Requestable interface
        
        $script_location = "../" . trim($desired_entry->file_name, "/");
        
        //Go to the location of the script
        chdir(dirname($script_location));
        
        //Include it
        require_once basename($desired_entry->file_name);
        		
        if (class_exists($desired_entry->class_name) == false) {
	        self::internal_error("Class ‘" . $desired_entry->class_name . "’ does not exist");
        }
        
        $instance = new $desired_entry->class_name;
        
        if ($instance instanceof APIEngine\Requestable) {
	        $instance->execute($request);
        } else {
	        self::internal_error("Class ‘" . $desired_entry->class_name . "’ does not implement interface <code>Requestable</code>");
        }

	}
	
	function __construct() {
		
		$this->method = $_SERVER["REQUEST_METHOD"];
		
		if (!in_array($this->method, [Method::GET, Method::POST, Method::PUT, Method::DELETE])) {
			self::internal_error("This server can only accept GET, POST, PUT and DELETE requests");
		}
		
		if (!file_exists("../.definition.json")) {
			self::internal_error("The endpoint definition file does not exist");
		}
		
		$redirect_tree_string = file_get_contents("../.definition.json");
		$this->redirect_tree = json_decode($redirect_tree_string, true);
		
		//PUT and DELETE parameters aren't stored inside $_REQUEST for some reason, so manually merge them
         
        if (in_array($this->method, [Method::PUT, Method::DELETE])) {
            $parameters = [];
            parse_str(file_get_contents("php://input"), $parameters);
             
            $_REQUEST = array_merge($_REQUEST, $parameters);
        }
        
        $this->arguments = array_filter(explode("/", $_REQUEST["arguments"]), function($value) {
	        return $value !== "";
	    });
               			
	}
	
}

$incoming_request = new APIRequest();
$incoming_request->execute();
	
?>