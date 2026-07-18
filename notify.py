import dbus
import dbus.mainloop.glib
from gi.repository import GLib
import subprocess

bus = None
notify = None
interface = None
currentRing = None
ringNotificationId = None
call = None

NOTIFICATION_AUDIO = "notification.wav"
RINGTONE_AUDIO = "ringtone.m4a"

def SendNotification(title, details, audio=None):
	interface.Notify(
		"telephony",
		dbus.UInt32(0),
		"",
		title,
		details,
		dbus.Array([], signature="s"),
		dbus.Dictionary({}, signature="sv"),
		dbus.Int32(5000))
	if audio != None:
		subprocess.Popen(['ffplay', '-nodisp', '-autoexit', "-nostats", audio])
		
def CallRing(number):
	global currentRing, ringNotificationId
	assert currentRing == None, "Multiple ring in-s should not exist!"
	ringNotificationId = interface.Notify(
		"telephony",
		dbus.UInt32(0),
		"",
		f"Incoming call from {number}",
		"Click to dismiss Call",
		dbus.Array([], signature="s"),
		dbus.Dictionary({}, signature="sv"),
		dbus.Int32(0))
	currentRing = subprocess.Popen(['ffplay', '-nodisp', '-autoexit', "-nostats", RINGTONE_AUDIO])
	subprocess.Popen(["python", "./phone.py"])
	
def OnNotificationClose(id, reason):
	global ringNotificationId, currentRing
	if ringNotificationId == id:
		currentRing.terminate()
		ringNotificationId = None
		currentRing = None
		call.HangUp()
		
def OnCallStatusUpdate(state):
	global ringNotificationId, currentRing
	if ringNotificationId != None and state != "ringingin":
		print(state)
		currentRing.terminate()
		interface.CloseNotification(dbus.Int32(ringNotificationId))
		ringNotificationId = None
		currentRing = None

def Initalize(sessionBus, SMS, TheCallsTM):
	global bus, notify, interface, call
	
	call = TheCallsTM
	bus = sessionBus
	notify = bus.get_object(
		"org.freedesktop.Notifications",
		"/org/freedesktop/Notifications")
	interface = dbus.Interface(
		notify,
		"org.freedesktop.Notifications")
		
	bus.add_signal_receiver(
		OnNotificationClose,
		signal_name="NotificationClosed",
		dbus_interface="org.freedesktop.Notifications")
		
	SMS.SubscribeSMSAdded(lambda m: SendNotification(f"New Message from {m['number']}", m["text"], NOTIFICATION_AUDIO))
	
	def OnNewCall(details):
		if not details["out"]:
			CallRing(details["number"])
	call.SubscribeCalls(OnNewCall)
	call.SubscribeStates(OnCallStatusUpdate)
	
	def OnStateChange(state):
		SendNotification(f'Modem State Updated: {state}', '')
	
	telephony = bus.get_object(
		"usr.telephony",
		"/usr/telephony")	
	interface = dbus.Interface(
		telephony,
		"usr.telephony")
	bus.add_signal_receiver(
		OnStateChange,
		signal_name="OnStateChange",
		dbus_interface="usr.telephony")
		
		
if __name__ == "__main__":
	dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
	Initalize(dbus.SessionBus())

