import sys
import re
import itertools

from Tokenizer import Token, EndpointToken, pairwise
from enum import Enum

class ParseError(Exception):
	"""An error name a bit more specific than just Exception"""
	pass


class Methods:
	"""Represents an HTTP method which could be sent to the server"""
	
	GET = "GET"
	POST = "POST"
	PUT = "PUT"
	DELETE = "DELETE"


class EndpointComponent:
	""" Represents an entry inside the tree. A wildcard component matches
		any non-null value, and a root components indicates the leaf node
		of the tree, where the RedirectEntry resides. """
	
	WILDCARD = "*"
	ROOT = "/"


class RedirectEntry:
	""" An entry at the end of the tree which describes how to invoke the
		code upon this endpoint being called. It contains the path of the
		file to call, the names of the parameters (if any), along with the
		class name which will reside inside the file. """
	
	def __init__(self, class_name, file_name, parameter_names = {}):
		self.parameter_names = parameter_names
		self.class_name = class_name
		self.file_name = file_name
	
	def dict_value(self):
		"""Returns a dictionary representation of itself"""
		return {"file": self.file_name, "class": self.class_name, "parameters": self.parameter_names}
	
	def __repr__(self):
		return str(self.dict_value())


class Scanner:
	""" Takes a series of tokens generated by the tokeniser and provides
		methods to interface with these tokens.
	"""
	
	def __init__(self, tokens):
		self.tokens = tokens
		self.current_token = tokens[0]
	
	def lookahead(self):
		"""Returns the token (and not the associated value) next in the list."""
		
		if type(self.current_token) is tuple:
			return self.current_token[0]
		else:
			return self.current_token
	
	def consume(self, *tokens):
		""" Pops a token off the top of the list and returns it, if the topmost
		 	element is one which is provided in the list of arguments. Otherwise
		 	it raises an exception. """
		
		if self.lookahead() in tokens:
			to_return = self.current_token
			
			self.tokens = self.tokens[1:]			
			self.current_token = None if len(self.tokens) == 0 else self.tokens[0]
			
			return to_return
		else:
			raise ParseError("expected one of " + str(tokens) + " but instead found " + str(self.lookahead()))


class Parser:
	""" This class takes a series of tokens generated by the tokeniser and constructs
		a 'tree' based on the structure of these tokens.
		
		The generated tree can be used to easily check the existence of an endpoint,
		and where one exists, what file it exists in, what class to invoke, and the
		names of parameters which should map to those sent as part of the request.
	"""
	
	def __init__(self, tokens):
		self.scanner = Scanner(tokens)
		self.base_dir = None
		self.tree = {}
	
	
	def parse(self):
		"""Parse the tokens and return a tree containing all endpoints in JSON form"""
		
		self.process_root_file()
		return self.tree


	def all_defined_classes(self):
		""" Returns all of the defined classes and files inside the tree in the form
		    (class_name, file_name). """
				
		def all_values(tree):
			for value in tree.values():
				if type(value) is dict:
					yield from all_values(value)
				else:
					yield (value.class_name, value.file_name)
		
		return set(all_values(self.tree))
		
	
	def endpoint_exists(self, method, components):
		""" Given endpoint components in the form (name, is_variable), returns whether
			an equivalent endpoint already exists inside the tree. """
		
		if not method in self.tree:
			return False # Obviously not in there
		
		sub_tree = self.tree[method]
		
		for name, is_variable in components:
			key = name if not is_variable else EndpointComponent.WILDCARD # Variables are wildcards
			
			if key in sub_tree:
				sub_tree = sub_tree[key] # Go down another level
			else:
				return False # Not a chance
		
		return EndpointComponent.ROOT in sub_tree # Should be true at this stage, but double check


	def readable_components(components):
		""" Given endpoint components in the form (name, is_variable), returns the
			human-readable representation of those components.
			
			Example:
			
			[('users', False), ('id', True), ('image', False)]
			returns '/users/[id]/image'
		"""
		
		decorated = []
		
		for name, is_variable in components:
			if is_variable: # Put it inside brackets
				decorated.append("[{0}]".format(name))
			else:
				decorated.append(name)
		
		return "/".join(decorated)

	
	# The following five methods comprise the recursive-descent parser
	
	def process_root_file(self):
		""" The initial parsing method. This method looks for acceptable
			tokens, and calls other methods to parse specific elements. """
		
		self.process_statement()
		
		while self.scanner.lookahead() in [Token.GROUP, Token.EXPORT, Token.BASE]:
			self.process_statement()
	
	
	def process_group(self):
		""" Parses a 'group' structure, with the following syntax:
		
			group <endpoint> (base <base directory>)?
			(	<export-directive>)+
		"""
		
		# Remove the 'group' keyword
		self.scanner.consume(Token.GROUP)
		
		# Now expect a series of components
		group_base_components = self.process_components()
		
		# Is there a base directory for this group?
		group_base = self.process_base(True) if self.scanner.lookahead() == Token.BASE else None
		
		# Now expect one or more export statements
		while self.scanner.lookahead() == Token.INDENT:
			self.scanner.consume(Token.INDENT)
			self.process_export(group_base_components, group_base)
	
	
	def process_base(self, should_return = False):
		""" Parses a 'base' directive, with the following syntax:
		
			base <directory>
			
			If `should_return` is True, return the directive value as opposed to
			setting the global base directory.
		"""
		
		self.scanner.consume(Token.BASE)
		_, base_value = self.scanner.consume(Token.STRING)
		
		base_value = '/' + base_value.strip("/")
		
		if should_return:
			return base_value
		else:
			self.base_dir = base_value
	
	
	def process_statement(self):
		""" Parses either a 'group', 'export' or 'base' directive by calling
			the appropriate parsing method, or by raising an exception if an
			unexpected token is found. """
		
		next = {
			Token.GROUP: self.process_group,
			Token.EXPORT: self.process_export,
			Token.BASE: self.process_base
		}
		
		if self.scanner.lookahead() in next:
			next[self.scanner.lookahead()]()
		else:
			raise ParseError("expected one of " + str(next.keys()) + " but instead found " + str(scanner.lookahead()))
	
	
	def process_components(self):
		""" Consumes a series of endpoint tokens, generated by the tokenizer, and returns a
			a list of nondeterministic endpoint components which can then be inserted into the
			tree (after being transformed into deterministic components). """
		
		# If there's a / at the front of the endpoint we don't really care
			
		if self.scanner.lookahead() == EndpointToken.SEPARATOR:
			self.scanner.consume(EndpointToken.SEPARATOR)
		
		if self.scanner.lookahead() in [Token.TO, Token.BASE]:
			return [] # This means there was just a / and nothing else
		
		endpoint_components = []
		
		# (variable | component | optional) *
		
		component_value = lambda t, v: (v, t is EndpointToken.VARIABLE, t is EndpointToken.OPTIONAL)
		token, value = self.scanner.consume(EndpointToken.COMPONENT, EndpointToken.VARIABLE, EndpointToken.OPTIONAL)
		
		# add (name, is_variable, is_optional)
		endpoint_components.append(component_value(token, value))
		
		while self.scanner.lookahead() == EndpointToken.SEPARATOR:
			self.scanner.consume(EndpointToken.SEPARATOR)
			
			if self.scanner.lookahead() in [Token.TO, Token.BASE]:
				break
			
			token, value = self.scanner.consume(EndpointToken.COMPONENT, EndpointToken.VARIABLE, EndpointToken.OPTIONAL)
			endpoint_components.append(component_value(token, value))
		
		#take these non-deterministic components and return deterministic ones
		
		return endpoint_components
	
	
	def process_export(self, endpoint_prefix_components = None, path_prefix = None):
		""" Parses an 'export' directive, which has the following syntax:
		
			export <http-method> <endpoint> to <class> in <file>
			
			It transforms the endpoint into a series of components, and then generates
			all possible 'paths' this endpoint could take (which could arise when variable
			parameters are optional).
		"""
		
		http_method_map = {Token.GET: Methods.GET,
						   Token.PUT: Methods.PUT,
						   Token.POST: Methods.POST,
						   Token.DELETE: Methods.DELETE}
		
		self.scanner.consume(Token.EXPORT)
		
		token = self.scanner.consume(Token.GET, Token.POST, Token.PUT, Token.DELETE)
		http_method = http_method_map[token]
		
		# Process the endpoint components next
		
		nondeterministic_endpoints = self.process_components()
			
		if endpoint_prefix_components is not None:
			nondeterministic_endpoints = endpoint_prefix_components + nondeterministic_endpoints
		
		# Make them all deterministic so we can insert them into the tree
		
		endpoints = self.deterministic_components(nondeterministic_endpoints)
		
		self.scanner.consume(Token.TO)
		
		# Class name comes next
		_, class_name = self.scanner.consume(Token.STRING)
		
		self.scanner.consume(Token.IN)
		
		# Finally the file name
		_, file_name = self.scanner.consume(Token.STRING)
		
		# Add the base directory and path prefix if they exist
		# base_dir + path_prefix + file_name
		
		prepend = (self.base_dir or "")
		
		if path_prefix is not None:
			prepend += '/' + path_prefix.strip('/')
		
		file_name = prepend + '/' + file_name.strip('/')
			
		# Add these endpoints to the tree, but first make sure an equivalent path doesn't already exist
		
		for endpoint in endpoints:
			if self.endpoint_exists(http_method, endpoint):
				raise ParseError("redefinition of endpoint ‘{0}’ for HTTP method ‘{1}’".format(readable_components(endpoint), http_method))
		
		if not http_method in self.tree:
			self.tree[http_method] = {}
		
		# Actually insert the RedirectEntry into the tree for each endpoint
		
		for endpoint in endpoints:
					
			# Figure out the parameters and their positions
			parameters = {i: name for i, (name, is_variable) in enumerate(endpoint) if is_variable}
			entry = RedirectEntry(class_name, file_name, parameters)
			
			current = self.tree[http_method]
			
			for name, is_variable in endpoint:
				key = name if not is_variable else EndpointComponent.WILDCARD # Variables translate to wildcards
				
				if not key in current:
					current[key] = {}
				
				current = current[key]
	
			# The end of the tree is here and this is where our entry belongs
			current[EndpointComponent.ROOT] = entry
	
	
	def deterministic_components(self, nondeterministic_components):
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
				raise ParseError("two consecutive optional components introduces unresolvable ambiguity between parameters ‘{0}’ and ‘{1}’".format(parameter_name1, parameter_name2))
			
		# Make sure parameter names aren't reused
			
		parameter_names = [name for name, is_variable, _ in nondeterministic_components if is_variable]
		all_duplicate_parameters = list(set(name for name in parameter_names if parameter_names.count(name) > 1))
			
		if len(all_duplicate_parameters) > 0:
			raise ParseError("parameter name ‘{0}’ is used more than once".format(all_duplicate_parameters[0]))
			
		# If there are no optionals, we're done (base case)
			
		optionals_exist = any(is_optional for _, _, is_optional in nondeterministic_components)
			
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
					components_copy[i] = (name, True, False) # (name, is a variable, isn't an optional)
					first_optional_index = i
					
					break # Only want the first one
			
			concrete_optional_paths = self.deterministic_components(components_copy)
			
			# Remove the first optional and recurse
			
			optional_removed_copy = nondeterministic_components[:]
			del optional_removed_copy[first_optional_index]
			
			without_optional_paths = self.deterministic_components(optional_removed_copy)
			
			# total paths = paths without optional + paths with optional as a variable
			
			return concrete_optional_paths + without_optional_paths