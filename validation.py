import re

def valid_username(username):
	USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
	return USER_RE.search(username)

def valid_password(password):
	PASSWORD_RE = re.compile(r"^.{3,20}$")
	return PASSWORD_RE.search(password)

def verify_password(password, verify):
	return password == verify

def valid_email(email):
	EMAIL_RE = re.compile(r"^[\S]+@[\S]+\.[\S]+$")
	return not email or EMAIL_RE.search(email)