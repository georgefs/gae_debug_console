import webapp2


class MainPage(webapp2.RequestHandler):
    def get(self):
        raise Exception('test')
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.write("hello world")

application = webapp2.WSGIApplication([
    ('/', MainPage),
], debug=True)


from backlash import DebuggedApplication
application = DebuggedApplication(application, evalex=True)
