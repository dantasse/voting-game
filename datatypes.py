#!/usr/bin/python
from google.appengine.ext import db

class Game(db.Model):
  name = db.StringProperty(required = True)

class ThingToDo(db.Model):
  name = db.StringProperty(required = True)
  game = db.ReferenceProperty(Game, required = True)

class Vote(db.Model):
  user = db.UserProperty(required = True)
  thingToDo = db.ReferenceProperty(ThingToDo, required = True)
  score = db.IntegerProperty(required = True)

# App Engine question:
# ThingToDo and Vote both have a ReferenceProperty.  I could make those "parent"
# relationships instead.  ReferenceProperty seems like the "right" way, but I
# don't know why.  Is that right?