import iLertIncident, time
from optparse import OptionParser 

# Variable definition
#path = "/home/nagios/Documents/writetext.txt"
#apikey = "2jfas5f7t892hf43z7532j4"
#host = 'mustino.ilertnow.com'

# Define nagios plugin options
parser = OptionParser("iLertPlugin.py -m [nagios|cronjob] -a Apikey -i iLertHost -p Writepath")
parser.add_option("-m", "--mode", dest="mode", help="Execution mode [nagios|cronjob]")
parser.add_option("-a", "--apikey", dest="apikey", help="Apikey for authentication in nagios mode")
parser.add_option("-i", "--iLerthost", dest="host", help="iLert hostname like ***.ilertnow.com")
parser.add_option("-p", "--path", dest="path", help="Path for write the incident")
(options, args) = parser.parse_args()

# Define nagios plugin parameters
mode = ""
apikey = ""
host = ""
path = ""

# Check if parameters are set
if (options.mode != "") and (options.apikey != "") and (options.host != "") and (options.path != ""): 
	mode = options.mode
	apikey = options.apikey
	host = options.host
	path = options.path
else:
	parser.error("The nagios iLertPlugin expect exactly four arguments to start.")
	

# Send incident to iLert
try:	
	if mode == "nagios": 
		xmldoc = ""
		xmldoc = iLertIncident.create(apikey)					
		
		# Write with mode 0 = temporarly (postfix *.tmp)
		tmpFilename = ""
		tmpFilename = iLertIncident.write(path, xmldoc, 0)
		
		if tmpFilename == "":
			raise Exception("8001")
		
		s_result = iLertIncident.send(host, xmldoc)
		
		if s_result != 0:			
			# Write with mode 1 = finally (postfix *.ilert)
			iLertFilename = iLertIncident.write(path, xmldoc, 1)			
			iLertIncident.delete(tmpFilename)
			
			if iLertFilename == "":
				raise Exception("8002")
		else:
			iLertIncident.delete(tmpFilename)
			
	elif mode == "cronjob":
		incidentList = iLertIncident.readList(path)
		if len(incidentList) > 0:
			for alert in incidentList:
				if alert.endswith(".ilert"):
					pos = incidentList.index(alert)
					del incidentList[pos]	
					rfile = "%s/%s" % (path, alert)
					xmldoc = iLertIncident.readXmldoc(rfile)					
					s_result = iLertIncident.send(host, xmldoc)
					
					if s_result == 0:
						iLertIncident.delete(rfile)						
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
