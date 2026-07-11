import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib
from datetime import datetime
import json

import SMS
import call
import data
import notify

print("telephony daemon starting...")
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
systemBus = dbus.SystemBus()
sessionBus = dbus.SessionBus()

SMS.Initalize(systemBus)
call.Initalize(systemBus)
notify.Initalize(sessionBus, SMS, call)

MESSAGES_PATH = 'texts/messages'
CALLS_PATH = 'calls/history'
CONTACTS_PATH = 'contacts'

def StoreMessage(message):
	path = MESSAGES_PATH + f"/{message['number']}"
	if data.Read(path) == None:
		data.CreateDirectory(path, [ message ])
	else:
		data.Add(path, message)
	daemon.SMSAdded(json.dumps(message))
SMS.SubscribeSMSAdded(StoreMessage)

def StoreCalls(details):
	details["timestamp"] = datetime.now().isoformat(timespec="seconds")
	data.Add(CALLS_PATH, details)
	daemon.NewIncomingCall(json.dumps(details))
call.SubscribeCalls(StoreCalls)

def OnStatesChange(state):
	daemon.CallStateUpdate(state)
	if state == "active":
		calls = data.Read(CALLS_PATH)
		data.Write(CALLS_PATH + f"/{len(calls) - 1}/answered", True)
call.SubscribeStates(OnStatesChange)

class Daemon(dbus.service.Object):
	def __init__(self, bus):
		super().__init__(bus, "/usr/telephony")
		print("registered!")
	
	
	@dbus.service.signal("usr.telephony", signature="s")
	def SMSAdded(self, message):
		pass
		
	@dbus.service.method("usr.telephony")
	def UpdateContact(self, number, name):
		if not number.isdigit():
			return
		
		contact = {
			'number': number,
			'name': name
		}
		if data.Read(CONTACTS_PATH).get(number) == None:
			data.CreateDirectory(CONTACTS_PATH + f"/{number}", contact)
			if data.Read(MESSAGES_PATH + f"/{number}") == None: 
				data.CreateDirectory(MESSAGES_PATH + f"/{number}", [])
		else:
			data.Write(CONTACTS_PATH + f"/{number}", contact)
				
	@dbus.service.method("usr.telephony", out_signaure="s")
	def GetMessagingHistory(self, number, start, end):
		messages = data.Read(MESSAGES_PATH + f"/{number}")
		if messages == None:
			return json.dumps(None)
		assert abs(start) > 0, "start and end prams are invalid"
		assert end >= start, "start and end prams are invalid"
		
		start = -min(abs(start), len(messages))
		end = -min(abs(end), len(messages))
		group = messages[end:start]
		return json.dumps(group)
		
	@dbus.service.method("usr.telephony", out_signaure="s")
	def GetMessagingOverview(self):
		messages = data.Read(MESSAGES_PATH)
		return json.dumps([*messages])
				
	@dbus.service.method("usr.telephony", out_signaure="s")
	def GetContacts(self):
		contacts = data.Read(CONTACTS_PATH)
		return json.dumps(contacts)
	
	@dbus.service.method("usr.telephony", in_signaure="ss")
	def SendMessage(self, number, text):
		SMS.SendMessage(number, text)
		message = {
			"number": f"{number}",
			"text": text,
			"timestamp": datetime.now().isoformat(timespec="seconds"),
			"sent": True,
			"read": True
		}
		StoreMessage(message)
			
	@dbus.service.method("usr.telephony")
	def MarkRead(self, number):
		messages = data.Read(MESSAGES_PATH + f"/{number}")
		for i in range(len(messages) - 1, 0, -1):
			if messages[i]["read"]:
				break
			data.Write(MESSAGES_PATH + f"/{number}/{i}/read", True)
		
	@dbus.service.signal("usr.telephony", signature="s")
	def NewIncomingCall(self, details):
		pass
		
	@dbus.service.signal("usr.telephony", signature="s")
	def CallStateUpdate(self, state):
		pass
		
	@dbus.service.method("usr.telephony")
	def MakeCall(self, number):
		call.MakeCall(number)
		
	@dbus.service.method("usr.telephony")
	def Answer(self):
		call.Answer()
		
	@dbus.service.method("usr.telephony")
	def HangUp(self):
		call.HangUp()
		
	@dbus.service.method("usr.telephony", out_signature="ss")
	def GetCallStatus(self):
		details, status = call.GetStatus()
		if status == None:
			status = ''
		return json.dumps(details), status
		
	@dbus.service.method("usr.telephony", out_signaure="s")
	def GetCallHistory(self, start, end):
		calls = data.Read(CALLS_PATH)
		assert abs(start) > 0, "start and end prams are invalid"
		assert end >= start, "start and end prams are invalid"
		
		start = -min(abs(start), len(calls))
		end = -min(abs(end), len(calls))
		group = calls[end:start]
		return json.dumps(group)
		
name = dbus.service.BusName("usr.telephony", sessionBus)

daemon = Daemon(sessionBus)

loop = GLib.MainLoop()
loop.run()
