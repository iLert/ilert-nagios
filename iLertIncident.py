import os, httplib, urllib, uuid

def create(apikey):
	# XML document start tag
	xmldoc = "<event><apiKey>%s</apiKey><payload>" % (apikey)
	
	# Read NAGIOS macros
	for env in os.environ:
		if ("NAGIOS_" in env):
			xmldoc += "<entry key=\"%s\">%s</entry>" % (env, os.environ[env])		
	
	# XML document end tag
	xmldoc += "</payload></event>"
	
	# For debugging 
	"""
	xmldoc +="<entry key=\"NAGIOS_HOSTADDRESS\">192.168.1.2</entry>"
	xmldoc +="<entry key=\"NAGIOS_HOSTNAME\">localhost</entry>"
	xmldoc +="<entry key=\"NAGIOS_HOSTOUTPUT\">Ping FAILED</entry>"
	xmldoc +="<entry key=\"NAGIOS_HOSTSTATE\">DOWN</entry>"
	xmldoc +="<entry key=\"NAGIOS_NOTIFICATIONTYPE\">PROBLEM</entry>"
	xmldoc +="</payload></event>"
	"""
	
	return xmldoc

def write(path, xmldoc, mode):
	# Write temporary file
	filename = ""
	
	if mode == 0:
		filename = "%s.tmp" % uuid.uuid4()
	else:
		filename = "%s.ilert" % uuid.uuid4()
	
	path += "/%s" % filename
	
	try:
		macrofile = open(path, "wb");
		macrofile.write(xmldoc)
		macrofile.close()
		return path
	except Exception as e:
		print type(e)
		print e.args
		return ""
		
		
def send(host, xmldoc):	
	headers = {"Content-type": "application/xml", "Accept": "application/xml"}
	data = ("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>")

	data +=xmldoc
	
	try:
		conn = httplib.HTTPConnection(host, 80, timeout=10)
		conn.request("POST", "/rest/events", data, headers)
		response = conn.getresponse()
	
		#For debugging
		#data = response.read()	
		#print data

		conn.close()
		
		#print "response.status %s" % response.status
		
		if (response.status == "200") or (response.reason == "OK"):
			return 0
		
		return 1
			
	except Exception as e:
		conn.close()
		print type(e)
		print e.args
		return 1


def readList(path):
	return os.listdir(path)
	
	
def readXmldoc(rfile):
	content = ""
	fobj = open(rfile, "r")
	for line in fobj: 
		content += line
	fobj.close()
	return content
	
def delete(rfile):
	os.remove(rfile)
	
