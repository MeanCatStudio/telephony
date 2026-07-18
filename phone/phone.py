import tkinter as tk
from tkinter import messagebox
from time import sleep
import dbus
import dbus.mainloop.glib
from gi.repository import GLib
import threading
import json
import sys
import fcntl
from datetime import datetime

DEFAULT_HISTORYS_LOAD = 20

LOCK_PATH = "/tmp/phone.lock"
def Singalton():
	lock = open(LOCK_PATH, 'w')
	#try:
	fcntl.lockf(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
	#except IOError:
	#	sys.exit(1)
		
Singalton()

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
bus = dbus.SessionBus()
telephony = bus.get_object(
	"usr.telephony",
	"/usr/telephony")
interface = dbus.Interface(
	telephony,
	"usr.telephony")

root = tk.Tk()
root.title("Phone")
root.geometry("400x600")

numPad = tk.Frame(root, relief=tk.RAISED, heigh=500, width=300, bg="lightgray")
numPad.pack_propagate(False)

number = tk.StringVar()
callState = tk.StringVar()
callState.set("N/A")
callingNumber = ""
display = tk.Entry(
	root,
	textvariable=number,
	font=("Arial", 24),
	justify="right",
	bd=10,
	width=16,
	relief='ridge'
)
display.pack()
numPad.pack()

buttons = [
	("1", 1, 0), ("2", 1, 1), ("3", 1, 2),
	("4", 2, 0), ("5", 2, 1), ("6", 2, 2),
	("7", 3, 0), ("8", 3, 1), ("9", 3, 2),
	("X", 4, 0), ("0", 4, 1), ("#", 4, 2)
]

for (text, row, col) in buttons:
	tk.Button(
		numPad,
		text=text,
		font=("Arial", 20),
		width=5,
		height=2,
		command=lambda t=text: OnNumpadClick(t)
	).grid(row=row, column=col, sticky="nsew")
	
canvasBorder = tk.Frame(root, width=305, bg='black', relief='raised', padx=2, pady=2)
canvas = tk.Canvas(canvasBorder)
scrollbar = tk.Scrollbar(canvasBorder, orient='vertical', command=canvas.yview)
canvas.configure(yscrollcommand=scrollbar.set)
messagingFrame = tk.Frame(canvas)
canvasWindow = canvas.create_window((0, 0), window=messagingFrame, anchor="nw")
messagingFrame.bind("<Configure>", lambda e: canvas.config(scrollregion=canvas.bbox('all')))
	
canvasBorder.pack(side='bottom', fill='y')
scrollbar.pack(side='right', fill='y')
canvas.pack(side='left', fill='both')

history = json.loads(interface.GetCallHistory(1, DEFAULT_HISTORYS_LOAD))
contacts = json.loads(interface.GetContacts())

def SetTitleOnState(state):
	root.title("Messages" if state == "cconnected" else "Messages - NOT CONNECTED")
SetTitleOnState(interface.GetStatus())
bus.add_signal_receiver(
	SetTitleOnState,
	signal_name="OnStateChange",
	dbus_interface="usr.telephony")

def FormateTime(time):
	age = datetime.now() - time
	if age.days < 1:
		return f"{time:%I:%M %p}"
	elif age.days < 2:
		return f"Yesterday"
	else:
		return f"{time:%Y-%m-%d}"
		
def Call(number):
	try:
		success, message = interface.MakeCall(number)
		callingNumber = number
	except dbus.exceptions.DBusException as e:
		success = False
		message = f"{e}"
		
	if not success:
		messagebox.showwarning("!!!", f"Failed to send message. \nError: {message}")
	return success

def CreateHistoryBlock(call):
	contact = contacts[call['number']]
	color = 'black' if call['answered'] else 'red'
	time = datetime.fromisoformat(call['timestamp']).replace(tzinfo=None)
	text = f"{'To' if call['out'] else 'From'} {contact["name"]} at {FormateTime(time)}"
	
	def OnRepeatCall(n):
		if Call(n):
			CallPage()
		
	button = tk.Button(messagingFrame, bg='white', text=text, font=("Arial", 16), width=30, foreground=color, relief='flat', command = lambda: OnRepeatCall(call['number']))
	button.pack(fill='x')
	
for i in range(len(history) - 1, 0, -1):
	CreateHistoryBlock(history[i])
	
def OnNumpadClick(char):
	if char == "#":
		if Call(number.get()):
			CallPage()
			number.set("")
	elif char == "X":
		number.set(number.get()[:-1])
	else:
		number.set(number.get() + char)
		
callButtons = {}
callPage = None
def CallPage():
	global callButtons, callPage
	callPage = tk.Toplevel()
	callPage.title('Call')
	callPage.geometry("400x600")
	
	contact = contacts.get(callingNumber, { "number": callingNumber, "name": callingNumber })
	tk.Label(callPage, font=("Arial", 24), textvariable=callState).pack(pady=20)
	tk.Label(callPage, font=("Arial", 36), text=f"{contact['name']}").pack()
	a = tk.Button(callPage, bg="green2", activebackground="green3", disabledforeground="darkgray", command = lambda: interface.Answer())
	a.place(x=50, y=450, height=100, width=100)
	b = tk.Button(callPage, bg="red2", activebackground="red3", disabledforeground="darkgray", command = lambda: interface.HangUp())
	b.place(x=250, y=450, height=100, width=100)
	callButtons = { "green": a, "red": b }
	
statusMapping = {
	"unknown": "N/A",
	"dialing": "Dialing",
	"ringingout": "Calling",
	"ringingin": "Call from",
	"active": "Active",
	"held": "Held",
	"waiting": "Waiting",
	"terminated": "Call Terminated"
}
	
def OnCallStatusUpdate(state):
	global callButtons, callPage
	print(state)
	callState.set(statusMapping[state])
	
	if (callPage == None):
		return
	if (state == "active" or state == "ringout" or state == "dialing"):
		callButtons["green"].config(state="disabled")
		callButtons["red"].config(state="normal")
	elif (state == "ringingin"):
		callButtons["green"].config(state="normal")
		callButtons["red"].config(state="normal")
	else:
		callButtons["green"].config(state="disabled")
		callButtons["red"].config(state="disabled")
	if (state== "terminated"):
		sleep(1)
		callPage.destroy()
		callButtons = {}
		callPage = None
	
bus.add_signal_receiver(
	OnCallStatusUpdate,
	signal_name="CallStateUpdate",
	dbus_interface="usr.telephony")

def OnNewCall(d):
	global callingNumber
	details = json.loads(d)
	
	if (not details["out"]):
		callingNumber = details["number"]
		OnCallStatusUpdate("ringingin")
		CallPage()
	
bus.add_signal_receiver(
	OnNewCall,
	signal_name="NewIncomingCall",
	dbus_interface="usr.telephony")
	
for i in range(5):
	numPad.rowconfigure(i, weight=1)
for i in range(3):
	numPad.columnconfigure(i, weight=1)
	
cc = None
def CheckForCall():
	global cc
	sleep(.5)
	details, status = interface.GetCallStatus()
	if status != "":
		OnNewCall(details)
		OnCallStatusUpdate(status)
	
loop = GLib.MainLoop()
loopThread = threading.Thread(target = loop.run)
loopThread.start()

cc = threading.Thread(target = CheckForCall)
cc.start()

root.mainloop()

loop.quit()
loopThread.join()
