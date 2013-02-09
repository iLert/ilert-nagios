########################################################################
# This is the iLert nagios plugin v1.0
# (c) by iLert 2013
# 
# File: iLertIncident.py
# Desc: iLert nagios plugin methods
########################################################################

# Libs
import os, fcntl, httplib, urllib, uuid

########################################################################
# Creates incident content with nagios macros from environment
########################################################################
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
	'''
	xmldoc +="<entry key=\"NAGIOS_HOSTADDRESS\">192.168.1.2</entry>"
	xmldoc +="<entry key=\"NAGIOS_HOSTNAME\">localhost</entry>"
	xmldoc +="<entry key=\"NAGIOS_HOSTOUTPUT\">Ping FAILED</entry>"
	xmldoc +="<entry key=\"NAGIOS_HOSTSTATE\">DOWN</entry>"
	xmldoc +="<entry key=\"NAGIOS_NOTIFICATIONTYPE\">PROBLEM</entry>"
	xmldoc +="</payload></event>"
	'''
	
	return xmldoc

########################################################################
# Writes incident as file to persist
########################################################################
def write(path, xmldoc):
	# Write temporary file
	filename = "%s.ilert" % uuid.uuid4()
	path += "/%s" % filename

	try:
		f = open(path, "wb")
		fd = f.fileno();
		fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
		f.write(xmldoc)
		f.close()
		return path
	except IOError:
		print("Write file (%s) blocked" % path)
		f.close()		
		return ""
    		
########################################################################
# Sends incident to iLert
########################################################################
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

########################################################################
# Cronjob reads all iLert files into a list which could not send
########################################################################
def readList(path):
	return os.listdir(path)
	
########################################################################
# Reads the content of all files from the list
########################################################################	
def readXmldoc(rfile):
	content = ""
	try:
		f = open(rfile, "r")
		fd = f.fileno();
		fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
		for line in f: 
			content += line
		f.close()
		return content
	except IOError:
		f.close()
		return "blocked"
	

########################################################################
# Deletes allready sent files
########################################################################	
def delete(rfile):
	os.remove(rfile)
	
