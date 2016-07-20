import sys
import os
import ctypes
import argparse
import json
import shutil

import Tokenizer
import Parser

from Parser import EndpointComponent

class CommonNames:
	EndpointDefinitionFile = ".endpoint"
	HypertextAccessFile = ".htaccess"

def json_from_definition_file():
	
	# Read the endpoint definition file from stdin
	
	file_stream = sys.stdin
	
	# Make some tokens out of it
	
	tokenizer = Tokenizer.Tokenizer(file_stream.read())
	tokens = tokenizer.all_tokens()
	
	# Parse and create a redirect tree from the tokens
	
	parser = Parser.Parser(tokens)
	out_tree = parser.parse()
	
	# Return a JSON-encoded object
	
	return json.dumps(out_tree)

def has_edit_permission():
	"""Returns True if the user is root/the Windows equivalent"""
	
	import ctypes

	try:
		return os.getuid() == 0
	except AttributeError:
		return ctypes.windll.shell32.IsUserAnAdmin() != 0


def create_project(project_directory, endpoint_definition_json):
	
	os.mkdir(project_directory)
	
	endpoint_definition_file = os.path.join(project_directory, CommonNames.EndpointDefinitionFile)
	
	with open(endpoint_definition_file, "w") as file:
		file.write(endpoint_definition_json)
		#os.chmod(file, 0o400)
	
	htaccess_file = os.path.join(project_directory, CommonNames.HypertextAccessFile)
	
	with open(htaccess_file, "w") as file:
		file.write("")
		#os.chmod(file, 0o600)


def update_project(project_directory, endpoint_definition_json):
	pass


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
	# We need to parse their endpoint definition file
	definition_file = json_from_definition_file()
	
	if arguments.mode == "create":
		create_project(project_directory, definition_file)
	else:
		update_project(project_directory, definition_file)