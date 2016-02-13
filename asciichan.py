import os
import webapp2
import jinja2
import urllib2
import logging
from xml.dom import minidom
from datetime import datetime

from google.appengine.api import memcache
from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), autoescape=True)

art_key = db.Key.from_path('ASCIIChan', 'ascii')

class Handler(webapp2.RequestHandler):
	def write(self, *a, **kw):
		self.response.out.write(*a, **kw)

	def render_str(self, template, **params):
		t = jinja_env.get_template(template)
		return t.render(params)

	def render(self, template, **kw):
		self.write(self.render_str(template, **kw))

GMAPS_URL = "http://maps.googleapis.com/maps/api/staticmap?size=380x263&sensor=false&zoom=3&"

def gmaps_img(points):
    markers = ["markers=%s,%s" % (point.lat, point.lon) for point in points]
    return GMAPS_URL + '&'.join(markers)

IP_URL = "http://api.hostip.info/?ip="
def get_coords(ip):
	url = IP_URL + ip
	content = None
	try:
		content = urllib2.urlopen(url).read()
	except urllib2.URLError:
		return

	if content:
		d = minidom.parseString(content)
		coords = d.getElementsByTagName("gml:coordinates")
		if coords and coords[0].childNodes[0].nodeValue:
			lon, lat = coords[0].childNodes[0].nodeValue.split(',')
			return db.GeoPt(lat, lon)

class Art(db.Model):
	title = db.StringProperty(required = True)
	art = db.TextProperty(required = True)
	created = db.DateTimeProperty(auto_now_add = True)
	coords = db.GeoPtProperty()

def top_arts(update=False):
	key = 'top'
	arts = memcache.get(key)
	#if not update and key in cache:
	if arts is None or update:
		logging.error("DB query")
		arts = list(db.GqlQuery("SELECT * FROM Art WHERE ANCESTOR IS :1 ORDER BY created DESC", art_key))
		#cache[key] = arts
		memcache.set(key, arts)
	return arts

class MainPage(Handler):
	def render_front(self, title="", art="", error=""):
		arts = top_arts()

		#find which arts have coords
		points = filter(None, (a.coords for a in arts))

		img_url = None
		if points:
			img_url = gmaps_img(points)

		#display the image url

		self.render("front.html", title=title, art=art, error=error, arts=arts, img_url=img_url)
	
	def get(self):
		#test: self.write(repr(get_coords(self.request.remote_addr)))
		self.render_front()

	def post(self):

		title = self.request.get("title")
		art = self.request.get("art")

		if title and art:
			p = Art(title = title, art = art, parent = art_key)
			coords = get_coords(self.request.remote_addr)
			if coords:
				p.coords = coords
			p.put()
			top_arts(True)

			self.redirect('/asciichan')
		else:
			error = "we need both a title and some artwork!"
			self.render_front(title, art, error)

app = webapp2.WSGIApplication([('/asciichan', MainPage)], debug=True)