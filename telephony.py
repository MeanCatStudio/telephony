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

MESSAGES_PATH = 'texts/messages'
CALLS_PATH = 'calls/history'
CONTACTS_PATH = 'contacts'

MODEM_STATES = [
	'failed',
	'unknown',
	'initalizing',
	'locked',
	'disabled',
	'enabling',
	'enabled',
	'searching',
	'registered',
	'disconnectinng',
	'connecting',
	'connected',
	'failed' # sometimes the state will be -1 which means failed
]

modem = systemBus.get_object(
	"org.freedesktop.ModemManager1",
	"/org/freedesktop/ModemManager1/Modem/0")
modemIface = dbus.Interface(
	modem,
	"org.freedesktop.DBus.Properties")

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

def OnCallStateChange(state):
	daemon.CallStateUpdate(state)
	if state == "active":
		calls = data.Read(CALLS_PATH)
		data.Write(CALLS_PATH + f"/{len(calls) - 1}/answered", True)
call.SubscribeStates(OnCallStateChange)

def OnModemStateChange(old, new, reason):
	daemon.OnStateChange(new)
	
systemBus.add_signal_receiver(
	OnModemStateChange,
	signal_name="StateChanged",
	dbus_interface="org.freedesktop.ModemManager1.Modem")

class InvalidArguments(dbus.DBusException):
	_dbus_error_name = 'usr.telephony.InvalidArugments'
	
class ModemUnavailable(dbus.DBusException):
	_dbus_error_name = 'usr.telephony.ModemUnavailable'

class Daemon(dbus.service.Object):
	def __init__(self, bus):
		super().__init__(bus, "/usr/telephony")
		print("registered!")
	
	@dbus.service.method("usr.telephony")
	def GetStatus(self):
		return MODEM_STATES[modemIface.Get("org.freedesktop.ModemManager1.Modem", "State")]
		
	@dbus.service.signal("usr.telephony", signature="s")
	def OnStateChange(self, state):
		pass
		
	@dbus.service.signal("usr.telephony", signature="s")
	def SMSAdded(self, message):
		pass
	
	@dbus.service.signal("usr.telephony", signature="s")
	def SMSAdded(self, message):
		pass
		
	@dbus.service.method("usr.telephony", signature="ss")
	def UpdateContact(self, number, name):
		if not number.isdigit():
			raise InvalidArguments("Provided arguments are invalid!")
		
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
		if abs(start) <= 0 or end < start:
			raise InvalidArguments("Start and End prams are invalid!")
		
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
		if not number.isdigit():
			raise InvalidArguments("Provided arguments are invalid!")
		if self.GetStatus() != 'connected':
			return False, 'Modem has not connected to netork'
			
		SMS.SendMessage(number, text)
		message = {
			"number": f"{number}",
			"text": text,
			"timestamp": datetime.now().isoformat(timespec="seconds"),
			"sent": True,
			"read": True
		}
		StoreMessage(message)
		return True, ''
			
	@dbus.service.method("usr.telephony", signature='s')
	def MarkRead(self, number):
		if not number.isdigit():
			raise InvalidArguments(f"Provided arguments are invalid!")
			
		messages = data.Read(MESSAGES_PATH + f"/{number}")
		if messages == None:
			raise InvalidArguments("Provided number does not have messsages!")
		
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
		
	@dbus.service.method("usr.telephony", signature="s")
	def MakeCall(self, number):
		if not number.isdigit():
			raise InvalidArguments("Provided number is invalid!")
		if self.GetStatus() != 'connected':
			return False, 'Modem has not connected to netork'
			
		call.MakeCall(number)
		return True, ''
		
	@dbus.service.method("usr.telephony")
	def Answer(self):
		if self.GetStatus() != 'connected':
			return False, 'Modem has not connected to netork'
			
		call.Answer()
		
	@dbus.service.method("usr.telephony")
	def HangUp(self):
		if self.GetStatus() != 'connected':
			return False, 'Modem has not connected to netork'
			
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
		
		if abs(start) <= 0 or end < start:
			raise InvalidArguments("Start and End prams are invalid!")
		
		start = -min(abs(start), len(calls))
		end = -min(abs(end), len(calls))
		group = calls[end:start]
		return json.dumps(group)
		
name = dbus.service.BusName("usr.telephony", sessionBus)

daemon = Daemon(sessionBus)
notify.Initalize(sessionBus, SMS, call)

loop = GLib.MainLoop()
loop.run()
