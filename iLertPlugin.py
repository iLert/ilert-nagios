########################################################################
# This is the iLert nagios plugin v1.0
# (c) by iLert 2013
# 
# File: iLertPlugin.py
# Desc: Main component of the iLert nagios plugin
########################################################################
 
import iLertIncident, time, os
from optparse import OptionParser 

# Variable definition
#path = "/home/nagios/Documents/writetext.txt"
#apikey = "2jfas5f7t892hf43z7532j4"
#host = 'mustino.ilertnow.com'

# Define nagios plugin options
parser = OptionParser("iLertPlugin.py -m {nagios|cronjob} [-a apikey] [-i iLertHost] -p Writepath")
parser.add_option("-m", "--mode", dest="mode", help="Execution mode [nagios|cronjob]")
parser.add_option("-a", "--apikey", dest="apikey", help="(optional) API-Key for the iLert-Account")
parser.add_option("-i", "--iLerthost", dest="host", help="(optional) iLert hostname like ***.ilertnow.com")
parser.add_option("-p", "--path", dest="path", help="Path for write the inncident")
(options, args) = parser.parse_args()


# Define nagios plugin parameters
mode = ""
apikey = ""
host = ""
path = ""

# Check if parameters are set
if (options.mode != None) and (options.path != None): 
	mode = options.mode	
	path = options.path
else:
	parser.error("The nagios iLertPlugin expect at least two arguments to start.")

# Optional parameter 'apikey'
if (options.apikey != None):
	apikey = options.apikey
else:
	apikey = os.environ['NAGIOS_CONTACTPAGER']

# Optional parameter 'host'
if (options.host != None):
	host = options.host
else:
	host = "ilertnow.com"


# Send incident to iLert
try:	
	if mode == "nagios": 
		xmldoc = ""
		xmldoc = iLertIncident.create(apikey)		
		
		# Persisting incident by writing file to filesystem
		filename = ""
		filename = iLertIncident.write(path, xmldoc)
		
		if filename == "":
			raise Exception("8001")
		
		s_result = iLertIncident.send(host, xmldoc)
				
		# Deletes persisted incident when sending succeeded
		if s_result == 0:			
			iLertIncident.delete(filename)
			
	elif mode == "cronjob":
		incidentList = iLertIncident.readList(path)
		if len(incidentList) > 0:			
			count = len(incidentList)
			i = 0
			alert = ''

			while i < count:
				alert = incidentList[i] 
				if alert.endswith(".ilert"):
					rfile = "%s/%s" % (path, alert)
					xmldoc = iLertIncident.readXmldoc(rfile)
					
					# if the current file is locked by another thread
					if (xmldoc == "blocked"):
						i+=1
						continue
						
					s_result = iLertIncident.send(host, xmldoc)
										
					if s_result == 0:
						iLertIncident.delete(rfile)	
				i+=1				
	else:
		parser.error("The iLert nagios plugin mode is not defined.")
		
except Exception as e:
	print type(e)
	print e.args
	t = time.strftime("%d%m%Y_%H-%M-%S")
	if e == "8001":		
		print "Nagios iLertPlugin could not write incident in file - Timestamp(%s)" %t
	else:
		print "An error occurs at running nagios iLertPlugin - Timestamp(%s)" %t
	exit(1)

exit(0)
