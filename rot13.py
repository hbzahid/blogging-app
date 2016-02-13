import webapp2
import cgi

form = """
<h2>Enter some text to ROT13:</h2>
<form method="post">
	<textarea name="text" style="height: 100px; width: 400px;">%(message)s</textarea>
	<br>
	<input type="submit">
</form>
"""

class MainPage(webapp2.RequestHandler):
	def write_form(self, message=""):
		self.response.out.write(form % {"message": encrypt_data(message)})

	def get(self):
		self.write_form()

	def post(self):
		message = self.request.get('text')
		self.write_form(message)

def encrypt_data(str):
	new_str = ''
	for each_char in str:
		if each_char.upper() >= 'A' and each_char.upper() <= 'M':
			new_str += chr(ord(each_char) + 13)
		elif each_char.upper() >= 'N' and each_char.upper() <= 'Z':
			new_str += chr(ord(each_char) - 13)
		else:
			new_str += each_char
	return escape_html(new_str)
			
def escape_html(str):
	return cgi.escape(str, quote = True)

app = webapp2.WSGIApplication([('/unit2/rot13', MainPage)], debug=True)