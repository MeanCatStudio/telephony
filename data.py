import json

FILEPATH = "./data.json"

""" Formate
data = {
	"calls": {
		"history": [
			1: {
				"number": 1234
				"time": [time]
				"out": True/False
				"answered": True/False
			}
		]
	},
	"texts": {
		"messages": {
			"[number #1]": [
				#messages
			]
			"[number #2]": [
				#messages
			]
		}
	}
	"contacts": {
		"[number #1]": {
			number, name
		}
	}
}
"""

data = None
with open(FILEPATH, "r") as file:
	data = json.load(file)
	
# path: text/messages/Number
def Read(path):
	current = data
	print("Reading", path)
	pathList = path.split('/')
	for step in pathList:
		if type(current) == dict:
			current = current.get(step)
		elif type(current) == list:
			assert step.isdigit(), "Path must provide an intger to read into lists"
			current = current[int(step)]
		if current == None:
			break
			
	if (step == pathList[-1]):
		return current
	else:
		return None
	
def Write(path, new):
	#print("Writting", path)
	
	pathList = path.split('/')
	obj = Read("/".join(pathList[:-1]))
	assert obj != None, "Path does not exsit"
	obj[pathList[-1]] = new
	UpdateJson()
	
def Add(path, new):
	#print("Adding", path)
	obj = Read(path)
	assert obj != None, "Path does not exsit"
	assert type(obj) == list, "Object is not a list"
	obj.append(new)
	UpdateJson()
	
def CreateDirectory(newPath, content):
	print("Creating", newPath)
	current = data
	prev = None
	for step in newPath.split('/'):
		prev = current
		current = current.get(step)
		if current == None:
			prev[step] = {}
			current = prev[step]
	prev[step] = content
	UpdateJson()

def UpdateJson():
	with open(FILEPATH, "w") as file:
		json.dump(data, file, indent = 4)
		
if __name__ == "__main__":
	print("Commands: v = view a directory, w = write in a location, c = create new path, q = quit")
	while True:
		command = input().lower().strip()
		if command == 'v':
			print(Read(input("Path: ")))
		elif command == 'w':
			Write(input("Path: "), input("Content: "))
			print('Written')
		elif command == 'c':
			CreateDirectory(input("Path: "), input("Content: "))
			print('Created')
		elif command == 'q':
			print("Quitting")
			break
		else:
			print("Unrecognized Command")
