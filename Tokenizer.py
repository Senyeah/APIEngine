import re
import itertools
from enum import Enum

def pairwise(iterable):
	"""s -> (s0,s1), (s1,s2), (s2,s3), ..."""
	
	a, b = itertools.tee(iterable)
	next(b, None)
	return zip(a, b)

class Token(Enum):
	""" Represents a token found in the high-level syntax, but before endpoint
		component parsing."""
	EXPORT, GROUP, BASE, INDENT, STRING, TO, IN, GET, POST, PUT, DELETE = range(11)

class EndpointToken(Enum):
	""" Represents a token found in the endpoint component parsing stage.
	
		In the following example:
			/image/[id]/[size]?
			
		* image is a component
		* / is the separator
		* id is a variable
		* size is an optional
	"""
	
	COMPONENT, SEPERATOR, VARIABLE, OPTIONAL = range(4)

class GenericTokenizer:
	""" Performs tokenisation in the most generic sense, given a list of (token, regex)
		pairs.
		
		The method for obtaining the actual tokens is specific to different types
		of tokens, so this is implemented by subclasses and as a result this class should
		not be instantiated by itself.
	"""
	
	def __init__(self, input_string, token_regexes):
		self.input_string = input_string
		self.current_char_index = 0
		self.token_regexes = token_regexes
		self.current_token = self.next_token()
	
	def skip_whitespace(self):
		
		""" Removes all whitespace from the current position in the string forward.
			Whitespace is defined as being either a space, newline, or carriage return.
		"""
		
		# Make sure we don't go over the length of the string
		if self.current_char_index >= len(self.input_string) - 1:
			return
		
		# Whitespace is defined as being one of either a space, newline or carriage return
		
		while self.input_string[self.current_char_index] in [' ', '\n', '\r']:
		
			# Sanity checking again
			if self.current_char_index < len(self.input_string) - 1:
				self.current_char_index += 1
			else:
				break
	
	def next_token(self):
		
		""" Attempts to match a token from the current position in the string forward.
			Longer matches are preferred, essentially to mimic Flex behaviour.
			
			Returns the token and its matched value, or None and an empty string if a
			match wasn't found.
		"""
		
		self.skip_whitespace()
		
		# We have nothing to begin with
		matched_value, token = '', None
		
		# Match for a token, starting at the top of the list downward
		
		for current_token, token_regex in self.token_regexes:
			match = re.match(token_regex, self.input_string[self.current_char_index:])
			
			# Prefer longer matches
			if match and match.end() > len(matched_value):
				matched_value, token = match.group(), current_token
		
		self.current_char_index += len(matched_value)
				
		return token, matched_value

class BaseTokenizer(GenericTokenizer):
	""" This is an implementation of a tokeniser for the high-level syntactic structure
		of an endpoint definition file. It does not parse endpoint components further,
		instead leaving this for a later stage.
	"""
	
	def all_tokens(self):
		""" Returns all tokens found in the tokenisation process. Return items are given
			as their token value if they aren't a string token, otherwise as a
			(token, string value) pair.
		"""
		
		tokens = []
		current_token, match = self.current_token

		# Tokenise the input and place the tokens into a list for further parsing

		while current_token is not None:
			if current_token == Token.STRING:
				tokens.append((Token.STRING, match[1:-1])) # Remove the quotes
			else:
				tokens.append(current_token)
			
			# Next one please
			current_token, match = self.next_token()
		
		return tokens

class EndpointTokenizer(GenericTokenizer):
	""" This is an implementation of a tokeniser for endpoint component strings.
		An example of an endpoint component string is: /image/[id]?/large/[type]
	"""
	
	def all_tokens(self):
		""" Returns all tokens found in the tokenisation process. Tokens are returned
			in the form (token, string value), unless it is a separator token, in
			which case only the separator token is added.
		"""
		
		tokens = []
		current_token, match = self.current_token

		# Tokenise the input and place the tokens into a list for further parsing

		while current_token is not None:
			string_value = None
			
			if current_token == EndpointToken.OPTIONAL:
				string_value = match[1:-2] # Remove the [ and ]?
			elif current_token == EndpointToken.VARIABLE:
				string_value = match[1:-1] # Remove the []
			elif current_token == EndpointToken.COMPONENT:
				string_value = match
			
			if string_value is None:
				tokens.append(current_token)
			else:
				tokens.append((current_token, string_value))
			
			# Next one please
			current_token, match = self.next_token()
		
		return tokens

class Tokenizer:
	""" Takes an input string containing an endpoint definition file and returns the
		tokens which it comprise. An exception is thrown if the input string is invalid.
	"""
	
	http_methods = [Token.GET, Token.POST, Token.PUT, Token.DELETE]
	
	# The regular expressions which define how the high-level code is initially matched
	token_regex = [
		(Token.EXPORT, 'export'),
		(Token.GROUP, 'group'),
		(Token.BASE, 'base'),
		(Token.TO, 'to'),
		(Token.IN, 'in'),
		(Token.GET, 'GET'),
		(Token.POST, 'POST'),
		(Token.PUT, 'PUT'),
		(Token.DELETE, 'DELETE'),
		(Token.INDENT, '\t'),
		(Token.STRING, '"[0-9a-zA-Z_/.\[\]\?\- ]+"')
	]
	
	# The regular expressions which define how the endpoint component strings are matched
	endpoint_token_regex = [
		(EndpointToken.SEPARATOR, '/'),
		(EndpointToken.OPTIONAL, '\[[A-Za-z0-9_]+\]\?'),			
		(EndpointToken.VARIABLE, '\[[A-Za-z0-9_]+\]'),
		(EndpointToken.COMPONENT, '[A-Za-z0-9_\-.]+')
	]
	
	def __init__(self, endpoint_definition_string):
		self.input_string = endpoint_definition_string
	
	def all_tokens(self):
		""" Performs parsing of the given input string, in two stages.
		
			First, it performs high-level tokenisation, and then scans the tokens for places
			where endpoint components could exist, and then further tokenises those.
			
			Returns a list of tokens, where entries are just either the token or a (token, value)
			pair if that token has meaning encapsulated in a value.
		"""
		
		
		# Obtain the set of tokens after the first pass of the tokenizer
		initial_tokens = BaseTokenizer(self.input_string, self.token_regex).all_tokens()
		
		# Then further parse endpoint strings, which come directly after either a HTTP method
		# or a group definition
		
		for index, (token, string_value_tuple) in enumerate(pairwise(initial_tokens)):
			
			if type(string_value_tuple) is tuple and (token in self.http_methods or token is Token.GROUP):
				
				# Parse the endpoint and insert the parsed tokens into the previously generated tokens
				index_to_replace = index + 1
				_, endpoint_string = string_value_tuple
				
				# Get the tokens from the endpoint string
				parsed_endpoint = EndpointTokenizer(endpoint_string, self.endpoint_token_regex).all_tokens()
				
				# Insert the new tokens and overwrite the old string token
				initial_tokens[index_to_replace:index_to_replace + 1] = parsed_endpoint
		
		return initial_tokens