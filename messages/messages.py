import tkinter as tk
from tkinter import messagebox
from datetime import datetime
from collections import deque
import json
import dbus
import dbus.mainloop.glib
from gi.repository import GLib
import threading

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
bus = dbus.SessionBus()
telephony = bus.get_object(
	"usr.telephony",
	"/usr/telephony")
interface = dbus.Interface(
	telephony,
	"usr.telephony")

DEFAULT_MESSAGES_LOADED = 20

messages = {}
for number in json.loads(interface.GetMessagingOverview()):
	messages[number] = json.loads(interface.GetMessagingHistory(number, 1, DEFAULT_MESSAGES_LOADED))
	print(interface.GetMessagingHistory(number, 1, DEFAULT_MESSAGES_LOADED))
contacts = json.loads(interface.GetContacts())

openedWindow = None
chatFrame = None
chatMessages = deque()

newMessageWindow = None

activeNumber = None

root = tk.Tk()
root.title("Messages")
root.geometry("320x600")

canvasBorder = tk.Frame(root, bg='black', relief='raised', padx=2, pady=2)
canvas = tk.Canvas(canvasBorder)
scrollbar = tk.Scrollbar(canvasBorder, orient='vertical', command=canvas.yview)
canvas.configure(yscrollcommand=scrollbar.set)
messagingFrame = tk.Frame(canvas)
canvasWindow = canvas.create_window((0, 0), window=messagingFrame, anchor="nw")
messagingFrame.bind("<Configure>", lambda e: canvas.config(scrollregion=canvas.bbox('all')))

bottomFrame = tk.Frame(root, height=60)
bottomFrame.pack(side='bottom', fill='x')
tk.Button(bottomFrame, text="new message", font=("Arial", 16), command=lambda: CreateNewMessageWindow()).pack(side="right")
tk.Button(bottomFrame, text="update contact", font=("Arial", 16), command=lambda: CreateNewContactWindow()).pack(side="left")

canvasBorder.pack(side='left', fill='both', expand=True)
scrollbar.pack(side='right', fill='y')
canvas.pack(side='left', fill='both', expand=True)

def SetTitleOnState(state):
	root.title("Messages" if state == "cconnected" else "Messages - NOT CONNECTED")
SetTitleOnState(interface.GetStatus())
bus.add_signal_receiver(
	SetTitleOnState,
	signal_name="OnStateChange",
	dbus_interface="usr.telephony")

def HasRead(number):
	if len(messages[number]) > 0:
		return messages[number][-1]["read"]
	return True

messageTabs = {}
def UpdateMessagingTab(contact, messages):
	number = contact["number"]
	color = "white" if HasRead(number) else "yellow"
	if (messageTabs.get(number) != None):
		messageTabs[number].config(text=contact["name"], bg=color, command=lambda: CreateChatWindow(contact, messages))
	else:
		button = tk.Button(messagingFrame, bg=color, font=("Arial", 20), width=20, text=contact["name"], relief='flat', command=lambda: CreateChatWindow(contact, messages))
		messageTabs[number] = button
		button.pack(fill='x')
	
for number in messages.keys():
	contact = contacts.get(number, { "number": number, "name": number })
	UpdateMessagingTab(contact, messages[number])
	
def CreateMessageGap(root):
	gap = tk.Frame(root, bg='white', height=10)
	gap.pack(side="top", fill="x")
	
def FormateTime(time):
	age = datetime.now() - time
	if age.days < 1:
		return f"Today {time:%I:%M %p}"
	elif age.days < 2:
		return f"Yesterday {time:%I:%M %p}"
	elif datetime.now().year - time.year < 1:
		return f"{time:%A, %B %d at %I:%M %p}"
	else:
		return f"{time:%B %d %Y at %I:%M %p}"
	
def CreateTimeBlock(root, prevTime, time):
	time = datetime.fromisoformat(time).replace(tzinfo=None)
	prevTime = datetime.fromisoformat(prevTime).replace(tzinfo=None)
	age = time - prevTime
	
	if age.total_seconds() > 3600:
		CreateMessageGap(root)
		label = tk.Label(root, 
			text = FormateTime(time),
			font=("Noto Color Emoji", 10))
		label.pack(side='top')
		
def CreateNewLine(root):
	CreateMessageGap(root)
	line = tk.Label(root, 
		text="new",
		bg="yellow",
		font=("Noto Color Emoji", 10))
	line.pack(side='top',fill="x")
	
def CreateMessageBlock(root, message):
	CreateMessageGap(root)
	
	messageFrame = tk.Frame(root, bg='white')
	messageFrame.pack(side='bottom', fill='x')
	sent = message['sent']
	text = tk.Label(root, 
		text= message['text']+' <' if sent else '> '+message['text'], 
		anchor= 'e' if message['sent'] else 'w', 
		justify= 'right' if message['sent'] else 'left',
		#wraplength=messageFrame.winfo_width(),
		font=("Noto Color Emoji", 14))
	text.bind("<Configure>", lambda e: text.config(wraplength=text.winfo_width()))
	text.pack(side='top', anchor='e' if sent else 'w')
	
	chatMessages.append(text)
	
def ResetOpenedWindow():
	global openedWindow, activeNumber, chatFrame
	activeNumber = None
	chatFrame = None
	openedWindow.destroy()
	openedWindow = None
	chatMessages.clear()
	return
	
def CreateChatWindow(contact, messages):
	global openedWindow, activeNumber, chatFrame
	if openedWindow != None:
		ResetOpenedWindow()
		if activeNumber == contact['number']:
			return
		
	def OnWindowDestroy():
		ResetOpenedWindow()
	
	activeNumber = contact['number']
	openedWindow = tk.Toplevel(root)
	openedWindow.title(f"{contact['name']} messages")
	openedWindow.geometry(f"520x600+{root.winfo_x() + 320}+{root.winfo_y()}")
	openedWindow.protocol("WM_DELETE_WINDOW", OnWindowDestroy)
	
	text = tk.StringVar()
	def Send():
		try:
			success, message = interface.SendMessage(activeNumber, text.get())
		except dbus.exceptions.DBusException as e:
			success = False
			message = f"{e}"
		if not success:
			messagebox.showwarning("!!!", f"Failed to send message. \nError: {message}")
	
	entryFrame = tk.Frame(openedWindow, bg='white')
	entryFrame.pack(side='bottom', fill='x')
	tk.Button(entryFrame, text='>', font=("Arial", 30), width=1, command=Send).pack(side='right')
	entry = tk.Entry(entryFrame, font=("Arial", 24), justify="left", bd=10, relief='ridge', textvariable=text)
	entry.pack(side='left', fill='x', expand=True)
	
	canvas = tk.Canvas(openedWindow, bg='white')
	scrollbar = tk.Scrollbar(openedWindow, orient='vertical', command=canvas.yview)
	canvas.configure(yscrollcommand=scrollbar.set)
	chatFrame = tk.Frame(canvas)
	canvasWindow = canvas.create_window((0, 0), window=chatFrame, anchor="nw")
	chatFrame.bind("<Configure>", lambda e: canvas.config(scrollregion=canvas.bbox('all')))
	canvas.bind('<Configure>', lambda e: canvas.itemconfig(canvasWindow, width=e.width))
	scrollbar.pack(side='right', fill='y')
	canvas.pack(side='left', fill='both', expand=True)
	
	newIndex = -1
	for i in range(len(messages) - 1, 0, -1):
		if (not messages[i]["read"]):
			newIndex = i
		else: 
			break
	
	prev =  { "timestamp":  "2000-01-01T00:00:00" } 
	for i in range(len(messages)):
		CreateTimeBlock(chatFrame, prev["timestamp"] , messages[i]["timestamp"])
		if (newIndex == i):
			CreateNewLine(chatFrame)
		CreateMessageBlock(chatFrame, messages[i])
		prev = messages[i]
		
	interface.MarkRead(activeNumber)	
	if len(messages) > 0:
		messages[-1]["read"] = True
	UpdateMessagingTab(contact, messages)
	canvas.yview_moveto(1.0)
	
def CreateNewMessageWindow():
	global openedWindow
	
	if openedWindow != None:
		ResetOpenedWindow()
	
	openedWindow = tk.Toplevel(root)
	openedWindow.title("new message")
	openedWindow.geometry(f"520x600+{root.winfo_x() + 320}+{root.winfo_y()}")
	
	number = tk.StringVar(value="number")
	def Send():
		try:
			success, message = interface.SendMessage(number.get(), text.get('1.0', '1.end'))
		except dbus.exceptions.DBusException as e:
			success = False
			message = f"{e}"
		if not success:
			messagebox.showwarning("!!!", f"Failed to send message. \nError: {message}")
			return
		ResetOpenedWindow()
	
	tk.Entry(openedWindow, font=("Arial", 24), justify="left", bd=10, relief='ridge', textvariable=number).pack(fill="x")
	tk.Button(openedWindow, text='Send', font=("Arial", 30), bd=5, command=Send).pack(side='bottom', fill='x')
	text = tk.Text(openedWindow, font=("Arial", 24), bd=10, relief='ridge')
	text.pack(fill="both", expand=True)
	
def CreateNewContactWindow():
	global openedWindow
	
	if openedWindow != None:
		ResetOpenedWindow()
	
	openedWindow = tk.Toplevel(root)
	openedWindow.title("new contact")
	openedWindow.geometry(f"520x600+{root.winfo_x() + 320}+{root.winfo_y()}")	
	
	number = tk.StringVar(value="number")
	name = tk.StringVar(value="name")
	def Create():
		ResetOpenedWindow()
	
	tk.Entry(openedWindow, font=("Arial", 24), justify="left", bd=10, relief='ridge', textvariable=number).pack(fill="x")
	tk.Entry(openedWindow, font=("Arial", 24), justify="left", bd=10, relief='ridge', textvariable=name).pack(fill="x")
	tk.Button(openedWindow, text='Confirm', font=("Arial", 30), bd=5, command=Create).pack(side='bottom', fill='x')
	
def UpdateContact(contact):
	number = contact["number"]
	contacts[number] = contact
	if messages.get(number) == None:
		messages[number] = []
	UpdateMessagingTab(contact, messages[number])
		
def AddMessage(m):
	message = json.loads(m)
	number = message["number"]
	contact = contacts.get(number, { "number": number, "name": number })
	if messages.get(number) == None:
		messages[number] = [ message ]
	else:
		messages[number].append(message)
		if (activeNumber == number):
			CreateMessageBlock(chatFrame, message)
	UpdateMessagingTab(contact, messages[number])
bus.add_signal_receiver(
	AddMessage,
	signal_name="SMSAdded",
	dbus_interface="usr.telephony")
	
loop = GLib.MainLoop()
loopThread = threading.Thread(target = loop.run)
loopThread.start()

root.mainloop()

loop.quit()
loopThread.join()
