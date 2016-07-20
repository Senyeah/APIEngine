import sys
import Tokenizer
import Parser

from Parser import EndpointComponent

# Read the endpoint definition file from stdin

file_stream = sys.stdin

tokenizer = Tokenizer.Tokenizer(file_stream.read())
tokens = tokenizer.all_tokens()

parser = Parser.Parser(tokens)
out_tree = parser.parse()

parse_request_string = lambda s: s.strip("/").split("/")

def redirect_entry_for_request(tree, method, components):
	if not method in tree:
		return None
	
	sub_tree = tree[method]
	current_item = 0
		
	while current_item < len(components):
		if components[current_item] in sub_tree.keys():
			sub_tree = sub_tree[components[current_item]]
			current_item += 1
		elif EndpointComponent.WILDCARD in sub_tree.keys():
			sub_tree = sub_tree[EndpointComponent.WILDCARD]
			current_item += 1
		elif len(components[current_item]) == 0:
			break
		else:
			return None
		
	if EndpointComponent.ROOT in sub_tree:
		return sub_tree[EndpointComponent.ROOT]
	else:
		return None

from pprint import pprint
pprint(out_tree)

print(redirect_entry_for_request(out_tree, Parser.Methods.GET, parse_request_string("/")))