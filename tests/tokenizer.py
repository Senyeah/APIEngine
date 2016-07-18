import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # Parent directory

import Tokenizer
from Tokenizer import Token, EndpointToken

import unittest

class TokenizationTests(unittest.TestCase):
	
	def test_base(self):
		
		definition_code = 'base "this is a test file"'
		expected_tokens = [Token.BASE, (Token.STRING, "this is a test file")]
	
		actual_tokens = Tokenizer.Tokenizer(definition_code).all_tokens()
		
		self.assertEqual(expected_tokens, actual_tokens)
	
	
	def test_export_simple(self):
		
		definition_code = 'export GET "/info" to "ClassName" in "FileName"'
		
		expected_tokens = [
			Token.EXPORT,
			Token.GET,
			EndpointToken.SEPARATOR,
			(EndpointToken.COMPONENT, "info"),
			Token.TO, 
			(Token.STRING, "ClassName"),
			Token.IN,
			(Token.STRING, "FileName")
		]
		
		actual_tokens = Tokenizer.Tokenizer(definition_code).all_tokens()
		
		self.assertEqual(expected_tokens, actual_tokens)
	
	
	def test_export_invalid(self):
		
		definition_code = 'export GET "@@INVALID@@" to "ClassName" in "FileName"'
		expected_tokens = [Token.EXPORT, Token.GET]
		
		actual_tokens = Tokenizer.Tokenizer(definition_code).all_tokens()
		
		self.assertEqual(expected_tokens, actual_tokens)
	
	def test_export_optional(self):
		
		definition_code = 'export GET "/users/[id]?/picture/[format]" to "UserImageRequest" in "file.php"'
		
		expected_tokens = [
			Token.EXPORT,
			Token.GET,
			EndpointToken.SEPARATOR,
			(EndpointToken.COMPONENT, "users"),
			EndpointToken.SEPARATOR,
			(EndpointToken.OPTIONAL, "id"),
			EndpointToken.SEPARATOR,
			(EndpointToken.COMPONENT, "picture").
			EndpointToken.SEPARATOR,
			(EndpointToken.VARIABLE, "format"),
			Token.TO,
			(Token.STRING, "UserImageRequest"),
			Token.IN,
			(Token.STRING, "file.php")
		]
		
		actual_tokens = Tokenizer.Tokenizer(definition_code).all_tokens()
		
		self.assertEqual(expected_tokens, actual_tokens)

	

if __name__ == '__main__':
	unittest.main()