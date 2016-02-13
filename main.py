import os, jinja2, webapp2, json, time
import utils
from google.appengine.api import memcache
from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)

class Handler(webapp2.RequestHandler):
	def write(self, *a, **kw):
		self.response.out.write(*a, **kw)

	def render_str(self, template, **params):
		user = self.user
		t = jinja_env.get_template(template)
		return t.render(params, user=user)

	def render(self, template, **kw):
		self.write(self.render_str(template, **kw))

	def login(self, user):
		self.set_secure_cookie('user_id', str(user.key().id()))

	def set_secure_cookie(self, name, value):
		self.response.headers.add_header('Set-Cookie', '%s=%s; Path=/' % (name, utils.make_secure_val(value)))

	def read_secure_cookie(self, name):
		cookie_val = self.request.cookies.get(name)
		return cookie_val and utils.check_secure_val(cookie_val)

	def logout(self):
		self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')

	def get_referer(self):
		return self.request.headers.get('referer', '/blog')

	def initialize(self, *a, **kw):
		webapp2.RequestHandler.initialize(self, *a, **kw)
		uid = self.read_secure_cookie('user_id')
		self.user = uid and User.get_by_id(int(uid))

#************
"Home Page"
#************

class HomePage(Handler):
	def get(self):
		self.render("home.html")

#*************************
"Blog implementation."
#*************************

def blog_key(name = 'default'):
	return db.Key.from_path('blogs', name)

class Blog(db.Model):
	subject = db.StringProperty(required=True)
	content = db.TextProperty(required=True)
	created = db.DateTimeProperty(auto_now_add=True)

	def replace(self):
		return self.content.replace('\n', '<br>')

	def to_dict(self):
		d = {"content": self.content, "created": self.created.strftime('%a %b %d %H:%M:%S %y'),
			"subject": self.subject}
		return d

class NewPost(Handler):
	def get(self):
		self.render("newpost.html")

	def post(self):
		subject = self.request.get('subject')
		content = self.request.get('content')

		if subject and content:
			entry = Blog(subject=subject, content=content, parent=blog_key())
			entry.put()
			entry_id = str(entry.key().id())
			top_posts(True)
			self.redirect('/blog/%s' % (entry_id))
		else:
			error = "Oops! Seems like you left either the title or the content field empty."
			self.render("newpost.html", subject = subject, content = content, error = error)

def top_posts(update=False):
	key = 'BLOGS'
	val = memcache.get(key)
	if val is None or update:
		posts = list(db.GqlQuery("SELECT * FROM Blog where ancestor is :1 ORDER BY created DESC LIMIT 10", blog_key()))
		val = (posts, time.time())
		memcache.set(key, val)
	return val

class BlogPage(Handler):
	def get(self):
		posts, query_time = top_posts()
		age = int(time.time() - query_time)
		self.render("blog.html", posts=posts, age=age)

def get_post(post_id):
	post_key = 'POST_' + post_id
	val = memcache.get(post_key)
	if val is None:
		post = Blog.get_by_id(int(post_id), parent=blog_key())
		val = (post, time.time())
		memcache.set(post_key, val)
	return val

class PostPage(Handler):
	def get(self, post_id):
		post, query_time = get_post(post_id)
		if post:
			age = int(time.time() - query_time)
			self.render("post.html", post=post, age=age)
		else:
			self.error(404)

class FlushCache(Handler):
	def get(self):
		memcache.flush_all()
		next_url = self.get_referer()
		self.redirect(next_url)

class permaJSON(Handler):
	def get(self, post_id):
		post = Blog.get_by_id(int(post_id), parent=blog_key())
		if post:
			self.response.headers['Content-Type'] = 'application/json; charset=UTF-8'
			self.write(json.dumps(post.to_dict()))

class BlogFrontJSON(Handler):
	def get(self):
		self.response.headers['Content-Type'] = 'application/json; charset=UTF-8'
		posts = top_posts()[0]
		j = json.dumps([post.to_dict() for post in posts]) 
		self.write(j)

#*************************
"Wiki implementation."
#*************************

def page_key(path):
	return db.Key.from_path('pages', 'wiki' + path)

class Article(db.Model):
	subject = db.StringProperty(required = True)
	content = db.TextProperty(required = True)
	created = db.DateTimeProperty(auto_now_add = True)
	last_modified = db.DateTimeProperty(auto_now = True)

	@classmethod
	def by_path(self, path):
		article = db.GqlQuery("SELECT * from Article where ancestor is :1 order by created desc", page_key(path))
		return article

def top_wikis(update=False):
	key = 'WIKIS'
	paths = memcache.get(key)
	if paths is None or update:
		keys = list(db.GqlQuery("SELECT __key__ FROM Article ORDER BY created DESC"))
		paths = [str(k.parent().name()) for k in keys]
		memcache.set(key, paths)
	return paths

class WikiMain(Handler):
	def get(self):
		paths = top_wikis()
		self.render('wiki-main.html', paths=paths)

class EditPage(Handler):
	def get(self, path):
		if not self.user:
			self.redirect('/login')
		else:
			article = Article.by_path(path).get()
			if article:
				self.render('wiki-edit.html', subject=article.subject, content=article.content, first_version=False)
				return
			self.render("wiki-edit.html", first_version=True)

	def post(self, path):
		if not self.user:
			self.error(400)
			return
		subject = self.request.get('subject')
		content = self.request.get('content')
		first_version = self.request.get('first-version')

		if subject and content:
			if first_version == "True":			
				page = Article(subject=subject, content=content, parent=page_key(path))
			else:
				page = Article.by_path(path).get()
				page.content = content
			page.put()
			top_wikis(True)
			self.redirect('/wiki' + path)
		else:
			error = "Oops! Seems like you left either the title or the content field empty."
			self.render("wiki-edit.html", subject = subject, content = content, error = error, first_version=True)

class WikiPage(Handler):
	def get(self, path):
		article = Article.by_path(path).get()
		if article:
			self.render("wiki-page.html", article=article, path=path)
		else:
			self.redirect('/wiki/_edit' + path)

#**********************************
"Authentication implementation."
#**********************************

class User(db.Model):
	name = db.StringProperty(required=True)
	password = db.StringProperty(required=True)
	email = db.StringProperty()

def set_errors(params):
	errors_dict = {}
	if not params['valid_user']:
			errors_dict['error_user'] = "That's not a valid username."
	if params['valid_pass']:
		if not params['passwords_match']:
			errors_dict['error_verify'] = "Your passwords didn't match."
	else:
		errors_dict['error_password'] = "The password must be at least 5 characters."
	if not params['email_valid']:
		errors_dict['error_email'] = "That's not a valid email."
	return errors_dict

class Signup(Handler):
	def get(self):
		next_url = self.get_referer()
		self.render("signup.html", next_url=next_url)

	def post(self):
		#next_url = str(self.request.get('next_url'))
		#if not next_url or next_url.startswith('/login'):
			#next_url = '/'

		username = self.request.get('username')
		password = self.request.get('password')
		verify = self.request.get('verify')
		email = self.request.get('email')

		valid_user = utils.valid_username(username)
		valid_pass = utils.valid_password(password)
		passwords_match = utils.verify_password(password, verify)
		email_valid = utils.valid_email(email)

		params = dict(valid_user = valid_user, valid_pass = valid_pass, 
			passwords_match = passwords_match, email_valid = email_valid)
 
 		errors = set_errors(params)

		if not errors:
			user_exists = db.GqlQuery("SELECT * FROM User WHERE name = :1", username).get()
			if not user_exists:
				new_user = User(name = username, password = utils.make_pw_hash(username, password), email = email)
				new_user.put()
				self.login(new_user)
				self.redirect('/wiki') # CHANGE THIS!!!
			else:
				error_user = "That user already exists."
				self.render("signup.html", error_user = error_user)	
		else:
			self.render("signup.html", username=username, email=email, **errors)

class Login(Handler):
	def get(self):
		next_url = self.get_referer()
		self.render("login.html", next_url=next_url)

	def post(self):
		username = self.request.get('username')
		password = self.request.get('password')

		#next_url = str(self.request.get('next_url'))
		#if not next_url or next_url.startswith('/login'):
			#next_url = '/blog'

		user = db.GqlQuery("SELECT * FROM User WHERE name = :1", username).get()
		if user and utils.valid_pw(username, password, user.password):
			self.login(user)
			self.redirect('/wiki')
		else:
			self.render("login.html", error=True)

class Logout(Handler):
	def get(self):
		next_url = self.get_referer()
		self.logout()
		self.redirect(next_url)

#*****************
"URI routing."
#*****************

PAGE_RE = r'<path:/(?:[a-zA-Z0-9_-]+/?)*>'
app = webapp2.WSGIApplication([webapp2.Route('/', handler=HomePage),
							   webapp2.Route('/blog', handler=BlogPage),
							   webapp2.Route('/blog/newpost', handler=NewPost),
							   webapp2.Route(r'/blog/<post_id:\d+>', handler=PostPage),
							   webapp2.Route('/blog/flush', handler=FlushCache),
							   webapp2.Route(r'/blog/<post_id:\d+>.json', handler=permaJSON),
							   webapp2.Route(r'/blog/.json', handler=BlogFrontJSON),
							   webapp2.Route('/signup', handler=Signup),
                               webapp2.Route('/login', handler=Login),
                               webapp2.Route('/logout', handler=Logout),
                               webapp2.Route('/wiki', handler=WikiMain),
                               webapp2.Route('/wiki/_edit' + PAGE_RE, handler=EditPage),
                               webapp2.Route('/wiki' + PAGE_RE, handler=WikiPage)
                               ],
                              debug=True)