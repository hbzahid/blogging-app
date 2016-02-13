import re, string, random, hashlib, hmac

secret = 'du.uyX9fE~Tb6.pp&U3D-0smYO,Gqi$^jS34tzu9'

def make_salt():
	return ''.join(random.sample(string.letters, 5))

def make_pw_hash(name, pw, salt=make_salt()):
	h = hashlib.sha256(name + pw + salt).hexdigest()
	return '%s|%s' % (h, salt)

def valid_pw(name, pw, h):
	salt = h.split('|')[1]
	return h == make_pw_hash(name, pw, salt)

def make_secure_val(s):
	return '%s|%s' % (s, hmac.new(secret, s).hexdigest())

def check_secure_val(h):
	val = h.split('|')[0]
	if h == make_secure_val(val):
		return val

def valid_username(username):
	USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
	return USER_RE.search(username)

def valid_password(password):
	PASSWORD_RE = re.compile(r"^.{5,20}$")
	return PASSWORD_RE.search(password)

def verify_password(password, verify):
	return password == verify

def valid_email(email):
	EMAIL_RE = re.compile(r"^[\S]+@[\S]+\.[\S]+$")
	return not email or EMAIL_RE.search(email)