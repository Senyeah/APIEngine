import sys
import re
import itertools
from pprint import pprint
from enum import Enum

def pairwise(iterable):
	"s -> (s0,s1), (s1,s2), (s2, s3), ..."
	a, b = itertools.tee(iterable)
	next(b, None)
	return zip(a, b)

class ParseError(Exception): #no
	pass

class Methods(Enum): #no
	GET, POST, PUT, DELETE = range(4)

class EndpointComponent(Enum): #no
	WILDCARD, ROOT = range(2)

class RedirectEntry: #no
	def __init__(self, class_name, file_name, parameter_names = {}):
		self.parameter_names = parameter_names
		self.class_name = class_name
		self.file_name = file_name
	
	def __repr__(self):
		return "(file='{0}', class='{1}', parameters={2})".format(self.file_name, self.class_name, str(self.parameter_names))

class Scanner:
	def __init__(self, tokens):
		self.tokens = tokens
		self.current_token = tokens[0]
	
	def lookahead(self):
		if type(self.current_token) is tuple:
			return self.current_token[0]
		else:
			return self.current_token
	
	def consume(self, *tokens):
		if self.lookahead() in tokens:
			to_return = self.current_token
			
			self.tokens = self.tokens[1:]			
			self.current_token = None if len(self.tokens) == 0 else self.tokens[0]
			
			return to_return
		else:
			raise ParseError("expected one of " + str(tokens) + " but instead found " + str(self.lookahead()))

#
# Tree
#

tree = {}

def endpoint_exists(method, components):
	if not method in tree:
		return False
	
	sub_tree = tree[method]
	
	for name, is_variable in components:
		key = EndpointComponent.WILDCARD if is_variable else name
		
		if key in sub_tree:
			sub_tree = sub_tree[key]
		else:
			return False
	
	return EndpointComponent.ROOT in sub_tree

def readable_components(components):
	decorated = []
	
	for name, is_variable in components:
		if is_variable:
			decorated.append("[{0}]".format(name))
		else:
			decorated.append(name)
	
	return "/".join(decorated)

#
# START THE RECURSIVE-DESCENT PARSER
#

scanner = Scanner(parsed_tokens)
base_dir = None

def process_root_file():
	process_statement()
	
	while scanner.lookahead() in [Token.GROUP, Token.EXPORT, Token.BASE]:
		process_statement()

def process_group():
	
	#get rid of the 'group' keyword
	scanner.consume(Token.GROUP)
	
	#now expect a series of components
	group_base_components = process_components()
	
	#is there a base directory for this group?
	group_base = process_base(True) if scanner.lookahead() == Token.BASE else None
	
	#now expect one or more export statements
	
	while scanner.lookahead() == Token.INDENT:
		scanner.consume(Token.INDENT)
		process_export(group_base_components, group_base)
	

def process_base(should_return = False):
	global base_dir
	
	scanner.consume(Token.BASE)
	_, base_value = scanner.consume(Token.STRING)
	
	base_value = '/' + base_value.strip("/")
	
	if should_return:
		return base_value
	else:
		base_dir = base_value

def process_statement():
	next = {
		Token.GROUP: process_group,
		Token.EXPORT: process_export,
		Token.BASE: process_base
	}
	
	if scanner.lookahead() in next:
		next[scanner.lookahead()]()
	else:
		raise ParseError("expected one of " + str(next.keys()) + " but instead found " + str(scanner.lookahead()))

def deterministic_components(nondeterministic_components):
	
	"""Given a list of components which may or may not be optional, returns a list
	   containing routes without any optional parameters, i.e. consider when that
	   optional is provided and when it isn't.
	
	   Components are given in the form (name, is_variable, is_optional), so
	   'image/[id]?/[size]/owner' would translate to:
	   
	   [('image', False, False), ('id', False, True), ('size', True, False), ('owner', False, False)]
	
	   Output components are given in the form (name, is_variable). No is_optional
	   is needed as the goal of this function is to remove optionals.
	
	   Examples:
		
	   image/[id]?/uid becomes
	
	       - image/[id]/uid
	       - image/uid
		
	   image/[a]/[b]?/c/[d]? becomes

	       image/[a]/[b]/c/[d]?
			    - image/[a]/[b]/c
			    - image/[a]/[b]/c/[d]
			
		   image/[a]/c/[d]?
				- image/[a]/c/[d]
				- image/[a]/c
	"""
		
	# Make sure we don't have two consecutive optional components
		
	for pair1, pair2 in pairwise(nondeterministic_components):
		
		parameter_name1, _, is_optional1 = pair1
		parameter_name2, _, is_optional2 = pair2
		
		if is_optional1 and is_optional2:
			raise ParseError("two consecutive optional components introduces unresolvable ambiguity between parameter names ‘{0}’ and ‘{1}’".format(parameter_name1, parameter_name2))
		
	# Make sure parameter names aren't reused
		
	parameter_names = [name for name, is_variable, _ in nondeterministic_components if is_variable]
	all_duplicate_parameters = list(set([name for name in parameter_names if parameter_names.count(name) > 1]))
		
	if len(all_duplicate_parameters) > 0:
		raise ParseError("parameter name ‘{0}’ is used more than once".format(all_duplicate_parameters[0]))
		
	# If there are no optionals, we're done (base case)
		
	optionals_exist = any([is_optional for _, _, is_optional in nondeterministic_components])
		
	if not optionals_exist:
		# Return it in the form [(name, is_variable), ...]
		return [[(name, is_variable) for name, is_variable, _ in nondeterministic_components]]
	else:
		# An optional parameter can either exist or not, so we need to find paths for both circumstances
		# Make the first optional we see a variable and not optional, then recurse
		
		components_copy = nondeterministic_components[:]
		first_optional_index = None
		
		for i in range(len(nondeterministic_components)):
			name, _, is_optional = components_copy[i]
			
			if is_optional:
				components_copy[i] = (name, True, False)
				first_optional_index = i
				
				break # Only want the first one
		
		concrete_optional_paths = deterministic_components(components_copy)
		
		# Remove the first optional and recurse
		
		optional_removed_copy = nondeterministic_components[:]
		del optional_removed_copy[first_optional_index]
		
		without_optional_paths = deterministic_components(optional_removed_copy)
		
		# total paths = paths without optional + paths with optional as a variable
		
		return concrete_optional_paths + without_optional_paths
	

def process_components():
	
	""" Consumes a series of endpoint tokens, generated by the tokenizer, and returns a
		a list of nondeterministic endpoint components which can then be inserted into the
		tree, after being transformed into deterministic components.
	"""
	
	#if there's a / at the front of the endpoint we don't really care
		
	if scanner.lookahead() == EndpointToken.SEPARATOR:
		scanner.consume(EndpointToken.SEPARATOR)
	
	if scanner.lookahead() in [Token.TO, Token.BASE]:
		return [] #this means there was just a / and nothing else
	
	endpoint_components = []
	
	# (variable | component | optional) *
	
	component_value = lambda t, v: (v, t is EndpointToken.VARIABLE, t is EndpointToken.OPTIONAL)
	token, value = scanner.consume(EndpointToken.COMPONENT, EndpointToken.VARIABLE, EndpointToken.OPTIONAL)
	
	# add (name, is_variable, is_optional)
	endpoint_components.append(component_value(token, value))
	
	while scanner.lookahead() == EndpointToken.SEPARATOR:
		scanner.consume(EndpointToken.SEPARATOR)
		
		if scanner.lookahead() in [Token.TO, Token.BASE]:
			break
		
		token, value = scanner.consume(EndpointToken.COMPONENT, EndpointToken.VARIABLE, EndpointToken.OPTIONAL)
		endpoint_components.append(component_value(token, value))
	
	#take these non-deterministic components and return deterministic ones
	
	return endpoint_components


def process_export(endpoint_prefix_components = None, path_prefix = None):
	
	global tree, base_dir
	
	http_method_map = {Token.GET: Methods.GET,
					   Token.PUT: Methods.PUT,
					   Token.POST: Methods.POST,
					   Token.DELETE: Methods.DELETE}
	
	scanner.consume(Token.EXPORT)
	
	token = scanner.consume(Token.GET, Token.POST, Token.PUT, Token.DELETE)
	http_method = http_method_map[token]
	
	nondeterministic_endpoints = process_components()
		
	if endpoint_prefix_components is not None:
		nondeterministic_endpoints = endpoint_prefix_components + nondeterministic_endpoints
	
	#make them all deterministic
	
	endpoints = deterministic_components(nondeterministic_endpoints)
	
	scanner.consume(Token.TO)
	
	#class name comes next
	_, class_name = scanner.consume(Token.STRING)
	
	scanner.consume(Token.IN)
	
	#finally the file name
	_, file_name = scanner.consume(Token.STRING)
	
	#add the base directory and path prefix if they exist
	#base_dir + path_prefix + file_name
	
	prepend = (base_dir or "")
	
	if path_prefix is not None:
		prepend += '/' + path_prefix.strip('/')
	
	file_name = prepend + '/' + file_name.strip('/')
		
	#add these endpoints to the tree, but first make sure an equivalent path doesn't already exist
	
	for endpoint in endpoints:
		if endpoint_exists(http_method, endpoint):
			raise ParseError("redefinition of endpoint ‘{0}’ for HTTP method ‘{1}’".format(readable_components(endpoint), http_method))
	
	if not http_method in tree:
		tree[http_method] = {}
	
	#actually insert the RedirectEntry into the tree for each endpoint
	
	for endpoint in endpoints:
				
		#figure out the parameters and their positions
		parameters = {i: name for i, (name, is_variable) in enumerate(endpoint) if is_variable}
		entry = RedirectEntry(class_name, file_name, parameters)
		
		current = tree[http_method]
		
		for name, is_variable in endpoint:
			key = name if not is_variable else EndpointComponent.WILDCARD # variables translate to wildcards
			
			if not key in current:
				current[key] = {}
			
			current = current[key]

		#the end of the tree is here and this is where our entry belongs
		
		current[EndpointComponent.ROOT] = entry

process_root_file()

####

parse_request_string = lambda s: s.strip("/").split("/")

def redirect_entry_for_request(method, components):
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

#pprint(tree)
#print(redirect_entry_for_request(Methods.GET, parse_request_string("/")))