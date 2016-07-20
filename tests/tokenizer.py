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
	
	
	def test_export_optional_variable(self):
		
		definition_code = 'export GET "/users/[id]?/picture/[format]" to "UserImageRequest" in "file.php"'
		
		expected_tokens = [
			Token.EXPORT,
			Token.GET,
			EndpointToken.SEPARATOR,
			(EndpointToken.COMPONENT, "users"),
			EndpointToken.SEPARATOR,
			(EndpointToken.OPTIONAL, "id"),
			EndpointToken.SEPARATOR,
			(EndpointToken.COMPONENT, "picture"),
			EndpointToken.SEPARATOR,
			(EndpointToken.VARIABLE, "format"),
			Token.TO,
			(Token.STRING, "UserImageRequest"),
			Token.IN,
			(Token.STRING, "file.php")
		]
		
		actual_tokens = Tokenizer.Tokenizer(definition_code).all_tokens()
		
		self.assertEqual(expected_tokens, actual_tokens)
	
	
	def test_group_no_optional(self):
		
		# Have to be careful of the indentation here
		
		definition_code = """group "/users" base "/user_code"
	export GET "/" to "UserGetRequest" in "user.php"
	export POST "/" to "UserCreateRequest" in "user.php" """
		
		expected_tokens = [
			Token.GROUP,
			EndpointToken.SEPARATOR,
			(EndpointToken.COMPONENT, "users"),
			Token.BASE,
			(Token.STRING, "/user_code"),
			Token.INDENT,
			Token.EXPORT,
			Token.GET,
			EndpointToken.SEPARATOR,
			Token.TO,
			(Token.STRING, "UserGetRequest"),
			Token.IN,
			(Token.STRING, "user.php"),
			Token.INDENT,
			Token.EXPORT,
			Token.POST,
			EndpointToken.SEPARATOR,
			Token.TO,
			(Token.STRING, "UserCreateRequest"),
			Token.IN,
			(Token.STRING, "user.php")
		]
		
		actual_tokens = Tokenizer.Tokenizer(definition_code).all_tokens()
				
		self.assertEqual(expected_tokens, actual_tokens)
	
	
	def test_group_variable(self):
		
		# Again be careful of the indentation
		
		definition_code = """group "/users/[id]" base "/user_code"
	export GET "/" to "UserGetRequest" in "user.php" """
	
		expected_tokens = [
			Token.GROUP,
			EndpointToken.SEPARATOR,
			(EndpointToken.COMPONENT, "users"),
			EndpointToken.SEPARATOR,
			(EndpointToken.VARIABLE, "id"),
			Token.BASE,
			(Token.STRING, "/user_code"),
			Token.INDENT,
			Token.EXPORT,
			Token.GET,
			EndpointToken.SEPARATOR,
			Token.TO,
			(Token.STRING, "UserGetRequest"),
			Token.IN,
			(Token.STRING, "user.php")
		]

		actual_tokens = Tokenizer.Tokenizer(definition_code).all_tokens()
		
		self.assertTrue(expected_tokens, actual_tokens)


	def test_group_optional(self):
		
		# Again be careful of the indentation
		
		definition_code = """group "/users/[id]?" base "/user_code"
	export GET "/" to "UserGetRequest" in "user.php" """
	
		expected_tokens = [
			Token.GROUP,
			EndpointToken.SEPARATOR,
			(EndpointToken.COMPONENT, "users"),
			EndpointToken.SEPARATOR,
			(EndpointToken.OPTIONAL, "id"),
			Token.BASE,
			(Token.STRING, "/user_code"),
			Token.INDENT,
			Token.EXPORT,
			Token.GET,
			EndpointToken.SEPARATOR,
			Token.TO,
			(Token.STRING, "UserGetRequest"),
			Token.IN,
			(Token.STRING, "user.php")
		]

		actual_tokens = Tokenizer.Tokenizer(definition_code).all_tokens()
		
		self.assertTrue(expected_tokens, actual_tokens)

if __name__ == '__main__':
	unittest.main()