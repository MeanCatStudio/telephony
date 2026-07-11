import dbus
import dbus.mainloop.glib
from gi.repository import GLib
import threading

CALLSTATES = [
	"unknown",
	"dialing",
	"ringingout",
	"ringingin",
	"active",
	"held",
	"waiting",
	"terminated"
]
MODEMPATH = "/org/freedesktop/ModemManager1/Modem/0"

#dbus.mainloop.glib.DBusGMainLoop(set_as_default = True)
bus = None #dbus.SystemBus()

activeCallPath = None
stateListeners = []
callListeners = []

modem = None
voice = None

def SubscribeCalls(func):
	callListeners.append(func)

def OnCallAdded(path):
	global activeCallPath
		
	#print(activeCallPath)
	if not activeCallPath:
		details = CreateCall(path)
		print("New incoming call", details["number"])
		for listener in callListeners:
			listener(details)
				
		activeCallPath = str(path)
		AttachMonitor(path)

def MakeCall(number):
	global activeCallPath
	if (activeCallPath):
		print("Cannot make call while one is active")
		return
	
	number = str(number).strip()
	if not number.isdigit():
		print("Invalid number")
		return
	
	activeCallPath = "Initalizing"
	callPath = voice.CreateCall({
		"number": f"{number}"
	})
	callIface = GetCallInterface(callPath)
	
	AttachMonitor(callPath)
	
	print("Dialing", number)
	activeCallPath = callPath
	callIface.Start()
		
	details = CreateCall(activeCallPath)
	details["out"] = True	
	for listener in callListeners:
		listener(details)
	
def CreateCall(path):
	call = bus.get_object("org.freedesktop.ModemManager1", path)
	props = dbus.Interface(call, "org.freedesktop.DBus.Properties")
	details = props.GetAll("org.freedesktop.ModemManager1.Call")
	return {
		"number": f"{details['Number'].strip('+')}",
		"timestamp": None,
		"out": details["Direction"] == 3,
		"answered": False
	}
	
def SubscribeStates(func):
	stateListeners.append(func)
	
def AttachMonitor(path):
	def OnCallPropertiesChanged(iface, change, invalid, path):
		global activeCallPath
		if iface != "org.freedesktop.ModemManager1.Call":
			return
			
		if "State" in change:
			state = CALLSTATES[change['State']]
			print("Call State Changed:", state)	
			for listener in stateListeners:
				listener(state)
			
			if state == "terminated":
				print("Call ended")
				activeCallPath = None
	
	bus.add_signal_receiver(
		OnCallPropertiesChanged,
		signal_name="PropertiesChanged",
		dbus_interface="org.freedesktop.DBus.Properties",
		path=path,
		path_keyword="path"
	)
	
def Answer():
	global activeCallPath
	if not activeCallPath:
		print("No incoming call")
		return
	
	callIface = GetCallInterface(activeCallPath)
	callIface.Accept()
	
def HangUp():
	global activeCallPath
	if not activeCallPath:
		print("No active call")
		return
		
	callIface = GetCallInterface(activeCallPath)
	callIface.Hangup()
	activeCallPath = None
	
def GetStatus():
	global activeCallPath
	if not activeCallPath:
		return None, None
	call = bus.get_object("org.freedesktop.ModemManager1", activeCallPath)
	props = dbus.Interface(call, "org.freedesktop.DBus.Properties")
	d = props.GetAll("org.freedesktop.ModemManager1.Call")
	details = CreateCall(activeCallPath)
		
	return details, CALLSTATES[d['State']]
	
def GetCallInterface(path):
	call = bus.get_object(
		"org.freedesktop.ModemManager1",
		path
	)
	return dbus.Interface(
		call,
		"org.freedesktop.ModemManager1.Call"
	)

def Initalize(systemBus):
	global bus, modem, voice
	bus = systemBus
	
	modem = bus.get_object(
		"org.freedesktop.ModemManager1",
		MODEMPATH)
	voice = dbus.Interface(
		modem,
		"org.freedesktop.ModemManager1.Modem.Voice")
	
	bus.add_signal_receiver(
		OnCallAdded,
		signal_name="CallAdded",
		dbus_interface="org.freedesktop.ModemManager1.Modem.Voice")

if __name__ == "__main__":
	dbus.mainloop.glib.DBusGMainLoop(set_as_default = True)
	Initalize(dbus.SystemBus())
	
	loop = None
	loopThread = None
	def Run():
		global loop, loopThread
		assert bus != None, "call was not initalized!"
		loop = GLib.MainLoop()
		loopThread = threading.Thread(target = loop.run)
		loopThread.start()
		
	def End():
		loop.quit()
		loopThread.join()
	
	Run()
	print("Commands: c = call, a = answer, h = hang up, q = quit")
	while True:
		command = input().lower().strip()
		if command == 'c':
			print("Making call")
			MakeCall(input("Numner: ").strip())
		elif command == 'a':
			print("Answering")
			Answer()
		elif command == 'h':
			print("Hanging Up")
			HangUp()
		elif command == 'q':
			print("Quitting")
			End()
			break
		else:
			print("Unrecognized Command")


