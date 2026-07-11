import dbus
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib
import threading

MODEMPATH = "/org/freedesktop/ModemManager1/Modem/0"

#DBusGMainLoop(set_as_default = True)

bus = None #dbus.SystemBus()

modem = None
messaging = None

def SendMessage(number, text):
	number = number.strip('+')
	if (not number.isdigit()):
		print(f"'{number}' has incorrect formating!")
		return
	path = messaging.Create({ "number": f"{number}", "text": text})
	sms = bus.get_object("org.freedesktop.ModemManager1", path)
	dbus.Interface(sms, "org.freedesktop.ModemManager1.Sms").Send()
	print("Message Sent")
	
def CreateMessage(details):
	message = {
		"number": f"{details['Number'].strip('+')}",
		"text": f"{details['Text']}",
		"timestamp": f"{details['Timestamp']}",
		"sent": details["PduType"] == 3,
		"read": details["PduType"] == 3
	}
	return message
	
SMSAddedListeners = []
def SubscribeSMSAdded(func):
	SMSAddedListeners.append(func)
	
def OnSMSAdded(path, recieved):	
	sms = bus.get_object("org.freedesktop.ModemManager1", path)
	props = dbus.Interface(sms, "org.freedesktop.DBus.Properties")
	details = props.GetAll("org.freedesktop.ModemManager1.Sms")
	
	if (not recieved):
		return
	
	print("New Message Recieved!")
	print(f"From: {details['Number']}")
	print(f"Message: {details['Text']}")
	message = CreateMessage(details)
	for func in SMSAddedListeners:
		func(message)
		
	ClearMessagingHistory()
	
def GetMessagingHistory():
	props = dbus.Interface(modem, "org.freedesktop.DBus.Properties")
	paths = props.Get("org.freedesktop.ModemManager1.Modem.Messaging", "Messages")
	
	messages = []
	for path in paths:
		sms = bus.get_object("org.freedesktop.ModemManager1", path)
		props = dbus.Interface(sms, "org.freedesktop.DBus.Properties")
		details = props.GetAll("org.freedesktop.ModemManager1.Sms")
		
		message = CreateMessage(details)
		messages.append(message)
		
	return messages
	
def ClearMessagingHistory():
	props = dbus.Interface(modem, "org.freedesktop.DBus.Properties")
	paths = props.Get("org.freedesktop.ModemManager1.Modem.Messaging", "Messages")
	
	for path in paths:
		messaging.Delete(path)

def Initalize(systemBus):
	global bus, modem, messaging
	bus = systemBus
	
	modem = bus.get_object(
		"org.freedesktop.ModemManager1",
		MODEMPATH)
	messaging = dbus.Interface(
		modem,
		"org.freedesktop.ModemManager1.Modem.Messaging")
		
	messaging.connect_to_signal("Added", OnSMSAdded)
	
if __name__ == "__main__":
	DBusGMainLoop(set_as_default = True)
	Initalize(dbus.SystemBus())
	
	loop = None
	loopThread = None
	def Run():
		global loop, loopThread
		assert bus != None, "SMS was not initalized!"
		loop = GLib.MainLoop()
		loopThread = threading.Thread(target = loop.run)
		loopThread.start()

	def End():
		loop.quit()
		loopThread.join()
	
	Run()
	print("Commands: w = send message, h = history, q = quit")
	while True:
		command = input().lower().strip()
		if command == 'w':
			SendMessage(input("Number: "), input("Text: "))
		elif command == 'h':
			messages = GetMessagingHistory()
			for message in messages:
				print(message)
		elif command == 'q':
			print("Quitting")
			End()
			break
		else:
			print("Unrecognized Command")
