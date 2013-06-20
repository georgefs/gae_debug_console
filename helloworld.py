import webapp2

from backlash import DebuggedApplication


class MainPage(webapp2.RequestHandler):

    def get(self):
        raise Exception('test')
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.write("hello world")

application = webapp2.WSGIApplication([
    ('/', MainPage),
], debug=True)

application = DebuggedApplication(application, evalex=True)
