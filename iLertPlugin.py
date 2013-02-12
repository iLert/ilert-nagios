########################################################################
# This is the iLert nagios plugin v1.2
# (c) by iLert 2013
# 
# File: iLertPlugin.py
# Desc: Main component of the iLert nagios plugin
########################################################################

# Libs
import iLertIncident, time, os, uuid, syslog
from optparse import OptionParser 

# Define nagios plugin options
parser = OptionParser("iLertPlugin.py -m {nagios|cronjob} [-a apikey] [-i iLertHost] [-p Port] -d Writepath")
parser.add_option("-m", "--mode", dest="mode", help="Execution mode [nagios|cronjob]")
parser.add_option("-a", "--apikey", dest="apikey", help="(optional) API-Key for the iLert-Account")
parser.add_option("-i", "--iLerthost", dest="host", help="(optional) iLert hostname like ***.ilertnow.com")
parser.add_option("-p", "--port", dest="port", help="(optional) host port - default port is 80")
parser.add_option("-d", "--directory", dest="path", help="Path/Directory for write the inncident")
(options, args) = parser.parse_args()


# Define nagios plugin parameters
mode = ""
apikey = ""
host = ""
port = ""
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

# Optional parameter 'port'
try:
	if (options.port != None):
		port = int(options.port)
		if (port <0 or port >65535):
			raise NameError('Portrange')
	else:
		port = 80
		
except ValueError as e:
	print type(e)
	print e.args	
	print "The port parameter have to be a number."
	raise
	
except NameError as e:
	print type(e)
	print e.args	
	print "Please choose a port between 0 and 65535."
	raise

# Send incident to iLert
try:	
	if mode == "nagios": 
		syslog.syslog('Nagios called iLert plugin...')
				
		# Create XML content
		xmldoc = ""		
		xmldoc = iLertIncident.create(apikey)
		incidentID = uuid.uuid4()
		
		# Create filename
		filename = ""
		filename = "%s.ilert" % incidentID	
		syslog.syslog('iLert nagios plugin created an incident %s' % incidentID)	
		
		# Persisting incident by writing file to filesystem
		path += "/%s" % filename 	
		f = open(path, "wb")
		res = iLertIncident.write(f, xmldoc)
		
		if res == 1:
			raise Exception("8001")
		
		syslog.syslog('iLert nagios plugin start to send incident %s...' % incidentID)
		#time.sleep(60)
		s_result = iLertIncident.send(host, port, xmldoc)		
		f.close()
		
		# Deletes persisted incident when sending succeeded
		if s_result == 0:			
			syslog.syslog('iLert nagios plugin sent incident %s successful.' % incidentID)
			iLertIncident.delete(path)
		else:
			syslog.syslog(syslog.LOG_ALERT, 'Sending incident failed and stored as %s' % filename)
		
	elif mode == "cronjob":
		syslog.syslog('Cronjob called iLert app...')
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
						
					syslog.syslog('iLert cronjob reads alert %s' % alert)	
					syslog.syslog('iLert cronjob start to send incident %s...' % alert)
					s_result = iLertIncident.send(host, port, xmldoc)
										
					if s_result == 0:
						syslog.syslog('iLert cronjob sent incident %s successful.' % alert)
						iLertIncident.delete(rfile)	
					else:
						syslog.syslog(syslog.LOG_ALERT, 'Sending incident failed and stored as %s' % alert)
				i+=1				
	else:
		parser.error("The iLert nagios plugin mode is not defined.")
		
except Exception as e:
	print type(e)
	print e.args
	f.close()
	t = time.strftime("%d%m%Y_%H-%M-%S")
	if e == "8001":		
		print "Nagios iLertPlugin could not write incident in file - Timestamp(%s)" %t
	else:
		print "An error occurs at running nagios iLertPlugin - Timestamp(%s)" %t
	exit(1)
except:
	f.close()
	print "Nagios iLertPlugin - Unexpected error:"
	exit(1)

exit(0)
