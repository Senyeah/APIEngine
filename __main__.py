import sys
import os
import ctypes
import argparse
import json
import shutil
from pprint import pprint

import Tokenizer
import Parser

from Parser import EndpointComponent

class CommonNames:
	EndpointDefinitionFile = ".definition.json"
	EndpointDefinitionReadableFile = ".definition"	
	HypertextAccessFile = ".htaccess"
	EngineDirectoryName = "engine"


def parse_definition_file(file_handle=sys.stdin):
	
	# Get the definition file
	definition_file = file_handle.read()
	
	# Make some tokens out of it
	
	tokenizer = Tokenizer.Tokenizer(definition_file)
	tokens = tokenizer.all_tokens()
	
	# Parse and create a redirect tree from the tokens
	
	parser = Parser.Parser(tokens)
	out_tree = parser.parse()
	
	# Return a JSON-encoded object
	
	json_object = json.dumps(out_tree, default=lambda x: x.dict_value())
	
	return definition_file, json_object, parser.all_defined_classes()


def has_edit_permission():
	"""Returns True if the user is root/the Windows equivalent"""
	
	try:
		return os.getuid() == 0
	except AttributeError:
		import ctypes
		return ctypes.windll.shell32.IsUserAnAdmin() != 0


def create_project(project_directory, endpoint_definition_readable, endpoint_definition_json, defined_classes):
	
	""" Creates a project, located at project_directory, with endpoint definition file
	    endpoint_definition_json. Classes and their respective files which are defined
	    are passes in the defined_classes argument, in the form (class_name, file_name).
	    
	    Files are copied from the /templates directory. The directories and files inside
	    the definition file are automatically recreated inside the project directory.
	"""
	
	script_run_location = os.path.dirname(os.path.realpath(__file__))
	script_templates_location = os.path.join(script_run_location, "templates")
	
	# Create the project's main directory
	os.mkdir(project_directory)
	
	# Create the project's `engine' directory
	engine_directory = os.path.join(project_directory, CommonNames.EngineDirectoryName)
	os.mkdir(engine_directory)
	
	# Write the human-readable endpoint definition file, used for modifications later on
	readable_definition_file = os.path.join(project_directory, CommonNames.EndpointDefinitionReadableFile)
	
	with open(readable_definition_file, "w") as file:
		file.write(endpoint_definition_readable)
	
	# Write the endpoint definition JSON
	endpoint_definition_file = os.path.join(project_directory, CommonNames.EndpointDefinitionFile)
	
	with open(endpoint_definition_file, "w") as file:
		file.write(endpoint_definition_json)
	
	# Important for security, read only
	os.chmod(endpoint_definition_file, 0o440)
	
	# Copy the htaccess file
	
	template_htaccess_location = os.path.join(script_templates_location, "htaccess")
	htaccess_file = os.path.join(project_directory, CommonNames.HypertextAccessFile)
	
	shutil.copyfile(template_htaccess_location, htaccess_file)
	
	# Copy the request handler and runtime files
	
	request_template_path = os.path.join(script_templates_location, "request.php")
	request_project_path = os.path.join(engine_directory, "request.php")
	
	runtime_template_path = os.path.join(script_templates_location, "runtime.php")
	runtime_project_path = os.path.join(engine_directory, "runtime.php")
	
	# Copy the request file
	shutil.copyfile(request_template_path, request_project_path)

	# ..and the runtime file
	shutil.copyfile(runtime_template_path, runtime_project_path)
	
	# Finally generate the class files
	
	class_definition_path = os.path.join(script_templates_location, "class-definition.php")
	
	with open(class_definition_path) as class_definition_file:
		class_definition_template = class_definition_file.read()
	
	single_class_template_path = os.path.join(script_templates_location, "class.php")
	
	with open(single_class_template_path) as class_template_file:
		single_class_template = class_template_file.read()	
	
	# We will create the following files, each with one or more classes inside
	
	files_to_create = {file_name: [] for _, file_name in defined_classes}
	
	# Create all of the defined directories if necessary
	
	for path in files_to_create.keys():
		full_path = os.path.join(project_directory, path.lstrip('/'))
		os.makedirs(os.path.dirname(full_path), exist_ok=True)
	
	# Now construct the individual PHP classes themselves
	
	for class_name, file_name in defined_classes:
		files_to_create[file_name].append(single_class_template.replace("[name]", class_name))
	
	# Finally we make the class files, comprised of one or more classes from above
	
	for file_name, classes in files_to_create.items():
	
		classes_string = "\n".join(classes)		
		class_file_path = os.path.join(project_directory, file_name.lstrip('/'))
		
		entire_class = class_definition_template.replace("[classes]", classes_string)
		
		# We need the path to the runtime file, so the class has access to the APIRequest namespace
		
		relative_runtime_path = os.path.relpath(runtime_project_path, os.path.dirname(class_file_path))
		entire_class = entire_class.replace("[include-directory-location]", relative_runtime_path)
		
		# Now finally write it
		
		with open(class_file_path, "w") as file:
			file.write(entire_class)


def update_project(project_directory, endpoint_definition_json):
	
	# Write the endpoint definition JSON
	endpoint_definition_file = os.path.join(project_directory, CommonNames.EndpointDefinitionFile)
	
	with open(endpoint_definition_file, "w") as file:
		file.write(endpoint_definition_json)

# Get the arguments from the command line

argument_parser = argparse.ArgumentParser()

argument_parser.add_argument("mode", help="The mode in which to execute, either ‘create’ to create a new project, ‘update’ to update an existing project, or ‘remove’ to permanently delete a project.")

argument_parser.add_argument("path", help="The path to the root directory of the project, where the project will either be created or updated from.", default="Untitled", nargs="?")

arguments = argument_parser.parse_args()

# Sanity checking

if arguments.mode not in ["create", "update", "remove"]:
	print("Error: mode must be one of create, update or remove", file=sys.stderr)
	sys.exit(1)
	
project_directory = os.path.join(os.getcwd(), arguments.path)

# If they're creating a new one, make sure no such project exists

if arguments.mode == "create":
	if os.path.exists(project_directory):
		print("Error: File or directory", arguments.path, "exists", file=sys.stderr)
		sys.exit(1)

# If they're updating or removing, make sure the project exists and
# that it is valid

if arguments.mode in ["update", "remove"]:
	if not os.path.isdir(project_directory):
		print("Error: no such project", arguments.path, file=sys.stderr)
		sys.exit(1)
	
	definition_file_path = os.path.join(arguments.path, CommonNames.EndpointDefinitionFile)
	
	if not os.path.exists(definition_file_path):
		print("Error: directory", arguments.path, "does not contain a valid project", file=sys.stderr)
		sys.exit(1)

# Need to be root to delete or update a project

if arguments.mode in ["update", "remove"] and not has_edit_permission():
	print("Error: must have administrative privileges to update or remove projects", file=sys.stderr)
	sys.exit(1)

# Now all of the sanity checks are complete, we can move on to actually
# doing something

if arguments.mode == "remove":
	shutil.rmtree(project_directory)
else:
	# Get the definition file's stream
	preexisting_file_path = os.path.join(project_directory, CommonNames.EndpointDefinitionReadableFile)
	stream = sys.stdin if arguments.mode == "create" else open(preexisting_file_path)
	
	# We need to parse their endpoint definition file
	original, parsed, defined_classes = parse_definition_file(stream)
	
	if arguments.mode == "create":
		create_project(project_directory, original, parsed, defined_classes)
	else:
		update_project(project_directory, parsed)		
		stream.close()