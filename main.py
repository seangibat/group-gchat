#!/usr/bin/env python

import os
import urllib
import jinja2
import webapp2
import uuid
import json
import datetime
import logging

from datetime import timedelta
from google.appengine.api import users
from google.appengine.ext import ndb
from google.appengine.api import channel
from google.appengine.api import taskqueue

JINJA_ENVIRONMENT = jinja2.Environment(
	loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
	extensions=['jinja2.ext.autoescape'],
	autoescape=True)

def chatroom_key(chatroom_name):
	return ndb.Key('Chatroom', chatroom_name)

def get_chats(chatroom):
	chats_query = ChatLine.query(ancestor=chatroom_key(chatroom)).order(+ChatLine.date)
	return chats_query.fetch()

def get_connections(chatroom):
	connections_query = Connection.query(ancestor=chatroom_key(chatroom))
	return connections_query.fetch(40)

def make_new_connection(chatroom, user):
	channel_id = uuid.uuid4().hex
	token = channel.create_channel(channel_id)
	ckey = chatroom_key(chatroom)

	# Store the connection
	connection = Connection(parent=ckey, token=token, channel_id=channel_id, user=user, chatroom=chatroom)
	connection.put()

	return connection

def send_json_to_chatroom_connections(message, chatroom):
	connections = get_connections(chatroom)
	for c in connections:
		channel.send_message(c.token, message)

def update_clients_connections_chatroom(chatroom):
	connections = get_connections(chatroom)
	u = []
	for c in connections:
		u.append(c.user.nickname())
	message = json.dumps({'type':'connectedUpdate','connections': u})
	for c in connections:
		channel.send_message(c.token, message)

def update_clients_connections_all():
	chat_connections_query = ndb.gql("SELECT DISTINCT chatroom FROM Connection")
	chat_connections = chat_connections_query.fetch()
	for chat_connection in chat_connections:
		chatroom = chat_connection.chatroom
		update_clients_connections_chatroom(chatroom)

class ChatLine(ndb.Model):
	author = ndb.UserProperty()
	content = ndb.StringProperty(indexed=False)
	date = ndb.DateTimeProperty(auto_now_add=True)

class Connection(ndb.Model):
	channel_id = ndb.StringProperty()
	token = ndb.StringProperty()
	chatroom = ndb.StringProperty()
	user = ndb.UserProperty()
	date = ndb.DateTimeProperty(auto_now_add=True)

class ChatPage(webapp2.RequestHandler):
	def get(self, chatroom="groupGchat"):
		current_user = users.get_current_user()
		connection = make_new_connection(chatroom, current_user)
		connections = get_connections(chatroom)
		chats = get_chats(chatroom)

		template_values = {
			'chatroom': urllib.quote_plus(chatroom),
			'token': connection.token,
			'chats': chats,
			'connections': connections,
			'user': current_user,
		}

		template = JINJA_ENVIRONMENT.get_template('index.html')
		self.response.write(template.render(template_values))

		update_clients_connections_chatroom(chatroom)

class ChatPost(webapp2.RequestHandler):
	def post(self):
		chatroom = self.request.get('chatroom')
		content = self.request.get('content')
		author = users.get_current_user()

		chatline = ChatLine(parent=chatroom_key(chatroom), content=content, author=author)
		chatline.put_async()

		message = json.dumps({'type':'chatMessage','content': content,'author': author.nickname()})
		send_json_to_chatroom_connections(message, chatroom)

class PollConnections(webapp2.RequestHandler):
	def get(self):
		connections_query = ndb.gql("SELECT token FROM Connection")
		connections = connections_query.fetch()
		message = json.dumps({'type':'test'})

		for c in connections:
			channel.send_message(c.token, message)

class UpdateConnectionTimestamp(webapp2.RequestHandler):
	def get(self):
		token = self.request.get('token')
		chatroom = self.request.get('chatroom')
		connection_query = Connection.query(Connection.token == token)
		connection = connection_query.get()
		self.response.out.write(connection)
		connection.date = datetime.datetime.now()
		connection.put()
		self.response.out.write(connection)

class PreenOldConnections(webapp2.RequestHandler):
	def get(self):
		time = datetime.datetime.now()-datetime.timedelta(minutes=6)
		key_query = ndb.gql("SELECT __key__ FROM Connection WHERE date <= :1", time)
		keys = key_query.fetch()
		self.response.out.write(keys)
		if keys:
			for k in keys:
				k.delete()
			update_clients_connections_all()
		
class ConnectionDisconnect(webapp2.RequestHandler):
	def post(self):
		channel_id = self.request.get('from')
		key_query = ndb.gql("SELECT __key__ FROM Connection WHERE channel_id = :1", channel_id)
		key_to_delete = key_query.get()
		connection = key_to_delete.get()
		chatroom = connection.chatroom
		key_to_delete.delete()
		update_clients_connections_chatroom(chatroom)

class ConnectionConnect(webapp2.RequestHandler):
	def post(self):
		return

app = webapp2.WSGIApplication([
	('/', ChatPage),
	('/chatpost', ChatPost),
	('/connections/testpoll', PollConnections),
	('/connections/updatetimestamp', UpdateConnectionTimestamp),
	('/connections/preen', PreenOldConnections),
	('/(\w+)', ChatPage),
	('/_ah/channel/connected/', ConnectionConnect),
	('/_ah/channel/disconnected/', ConnectionDisconnect)
], debug=True)