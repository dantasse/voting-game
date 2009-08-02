#!/usr/bin/python

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
import os
import logging
from google.appengine.ext.webapp import template
from datatypes import Game
from datatypes import ThingToDo
from datatypes import Vote

class MainPage(webapp.RequestHandler):
  def get(self):
    # HTML question: ugh, to save any state I have to pass the gameKey around.
    # I guess that's the nature of HTTP, though, right?
    # App Engine question: could I set a cookie instead?
    # App Engine question, part 2: devious Alice could easily hack into Bob's
    # voting game if she knew his game key.  Game keys are easy to guess.
    # How can I maintain state without relying on this brittle game key?
    # (also, a long alphanumeric nonsense string in the URL is ugly.)
    current_game = db.get(self.request.get('gameKey'))
    template_values = {
      "user": users.get_current_user(),
      "game": current_game,
      "thingsToDo": ThingToDo.all().filter("game = ", current_game),
      "message": self.request.get('message'),
      "voteValues": [1,2,3,4,5],
    }
    # boilerplate:
    path = os.path.join(os.path.dirname(__file__), 'index.html')
    self.response.out.write(template.render(path, template_values))

class GameSelectionPage(webapp.RequestHandler):
  def get(self):
    template_values = {
      "games": Game.all(),
    }
    self.response.out.write(template.render('select_game.html',
      template_values))

class GameCreator(webapp.RequestHandler):
  def post(self):
    newGame = Game(name=self.request.get('gameName'), state='creating')
    newGame.put()
    self.redirect("/?gameKey=" + str(newGame.key()))

class ThingAdder(webapp.RequestHandler):
  def post(self):
    # make a new ThingToDo that points to the game that it's in
    thing = ThingToDo(name = self.request.get('thingName'),
      game = db.get(self.request.get('gameKey')))
    thing.put()
    self.redirect("/main?gameKey=" + str(self.request.get('gameKey')))

class ThingDeleter(webapp.RequestHandler):
  def post(self):
    thing = db.get(self.request.get('thingKey'))
    gameKey = str(thing.game.key())
    message = "Deleted the following Thing To Do: " + thing.name
    # App Engine question:
    # If you delete a ThingToDo, all the Votes for it should be deleted too.
    # Is there any way to do this automatically?
    votes = db.GqlQuery("SELECT * FROM Vote WHERE thingToDo = :1", thing.key())
    for vote in votes:
      vote.delete()
    thing.delete()
    # HTTP question:
    # The "message" parameter I'm passing here is just a string, which can have
    # punctuation, spaces, etc.  This seems bad but doesn't actually fail in
    # practice.  (does it?)
    self.redirect("/main?gameKey=" + gameKey + "&message=" + message)

class Voter(webapp.RequestHandler):
  def post(self):
    thing = db.get(self.request.get("thingToDoKey"))
    query = Vote.gql("WHERE user = :1 AND thingToDo = :2",
      users.get_current_user(), thing)
    if (query.get()):
      # this user already voted on this thing; display an error
      # App Engine question:
      # Any way to do this validation client-side?
      self.redirect("/main?gameKey=" + str(self.request.get('gameKey')) +
        "&message=You've already voted on " + thing.name + ".")
      return
    try:
      score = int(self.request.get("score"))
      if (score < 1 or score > 5):
        raise ValueError, "Vote must be between 1 and 5"
      # if it can't parse your vote, it will also raise ValueError
    except ValueError:
      self.redirect("/main?gameKey=" + str(self.request.get('gameKey')) +
        "&message=Vote must be between 1 and 5")
      return

    vote = Vote(user = users.get_current_user(), thingToDo = thing,
      score = score)
    vote.put()
    message = "Recorded your vote of " + str(score) + " for " + thing.name
    self.redirect("/main?gameKey=" + str(self.request.get('gameKey')) +
      "&message=" + message)

class WinnerCalculator(webapp.RequestHandler):
  def get(self):
    current_game = db.get(self.request.get("gameKey"))
    scores = {}
    for thing in ThingToDo.all().filter("game = ", current_game):
      # App Engine question:
      # I use GQL sometimes and .filter() etc sometimes.  They're both
      # pretty intuitive to me.  Is either way faster or otherwise preferred?
      allVotes = Vote.gql("WHERE thingToDo = :1", thing)
      scores[thing] = 0
      for vote in allVotes.fetch(limit = 1000): # 1000 is the max limit.
      # App Engine question:
      # is there any way to say "give me everything in the data store, I don't
      # care how long it takes?"  The 1000 limit scares me; what if 1001 people
      # are voting on the same thing?  This will just miss 1 vote, silently.
        scores[thing] += vote.score
    self.response.out.write("Here are the totals:")
    for (thing, score) in scores.items():
      self.response.out.write("<br/>" + thing.name + " - " + str(score))

class LoggerOuter(webapp.RequestHandler):
  def post(self):
    self.redirect(users.create_logout_url("/"))

application = webapp.WSGIApplication([
                                     ('/', GameSelectionPage),
                                     ('/main', MainPage),
                                     ('/select_game', GameSelectionPage),
                                     ('/create_game', GameCreator),
                                     ('/add_thing', ThingAdder),
                                     ('/delete_thing', ThingDeleter),
                                     ('/vote', Voter),
                                     ('/calculate_winner', WinnerCalculator),
                                     ('/logout', LoggerOuter),
                                     ],
                                     debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
