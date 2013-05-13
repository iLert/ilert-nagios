#!/usr/bin/env python

# **************************************************************************
# * iLert Watchdog
# * This app checks if email processing functionality of iLert works fine
# * 
# * (c) by iLert, 2013
# **************************************************************************


# import libs
import httplib
import base64
import string
import time
import smtplib
import string
from xml.dom.minidom import parseString

# connection details
HOST = "ilertnow.com"
USERNAME = 'mustino@mustino'
PASS = 'ilertmantar80'
# alarmsource to check
ALARMSOURCE = "servercheck@mustino.ilertnow.com"
# max time (seconds) for iLert to processing emails
MAXTIMELIMIT = 10
# time to wait between sending email to iLert and the check process
WAITTIME = 10
# test email subject
SUBJECT = "iLert Watchdog Message"
CURTIMESTAMP = int(time.time())
TESTSUBJECT = "%s - %s" % (SUBJECT, CURTIMESTAMP)
# warning email subject
WARNINGSUBJECT = "iLert Watchdog Warning!"


#def timecalc(epochtime):
	#return hour, minutes and seconds

# Method for http request to the iLert REST-Interface
def wsRequest(url, httpmethod):
	
	message = ' '
 
	# base64 encode the username and password
	auth = base64.encodestring('%s:%s' % (USERNAME, PASS)).replace('\n', '')
 
	webservice = httplib.HTTP(HOST)
	# write your headers
	webservice.putrequest(httpmethod, url)
	webservice.putheader("Host", HOST)
	webservice.putheader("User-Agent", "Python http auth")
	webservice.putheader("Content-type", "text/html; charset=\"UTF-8\"")
	webservice.putheader("Content-length", "%d" % len(message))
	webservice.putheader("Authorization", "Basic %s" % auth) 
	webservice.endheaders()
	webservice.send(message)
	
	# get the response
	statuscode, statusmessage, header = webservice.getreply()
	
	# Debugging code
	print "Response: ", statuscode, statusmessage
	print "Headers: ", header
	
	if (statuscode == "200") | (statusmessage == "OK"):		
		return webservice.getfile().read()
	else:
		# send email with statuscode and reason and warning!
		sendWarningMail("statuscode - statusmessage")
		
	return 1
		

# Get all open incidents
def getOpenIncidents():
	return wsRequest("/rest/incidents/open", "GET")

# Close incident with the given incidentID
def closeIncident(incidentID):
	url = "/rest/incidents/resolve/%s" % incidentID
	print "url ", url
	res = wsRequest(url, "PUT")
	#print res

# Check if the sent email was processed and has the status of an opend incident
def checkIsMsgProcessed(xmldoc):	
	# parse the xml document 
	dom = parseString(xmldoc)	
	
	# variable declaration
	intkey = ""
	xmltag = ""
	timestamp = ""
	found = 0
	closed = 0
	counter = 0
	incidentLength = len(dom.getElementsByTagName('incident'))
	
	# search all opened incidents for the sent email
	while counter < incidentLength: 
		# save integrationkey
		intkey = dom.getElementsByTagName('incident')[counter].getElementsByTagName('integrationKey')[0].firstChild.nodeValue

		# if emailadress is correct		
		if intkey == ALARMSOURCE:

			# save subject, reporttime and incidentID
			subjectWithTime = dom.getElementsByTagName('incident')[counter].getElementsByTagName('subject')[0].firstChild.nodeValue
			reportTime = dom.getElementsByTagName('incident')[counter].getElementsByTagName('reportTime')[0].firstChild.nodeValue
			incidentID = dom.getElementsByTagName('incident')[counter].getElementsByTagName('id')[0].firstChild.nodeValue
			
			subArr = subjectWithTime.split(" - ")
			subject = subArr[0]
			timestamp = subArr[1]
						
			if subject == SUBJECT:
				found += 1
				print "subject ", subject	
				# remove milliseconds	
				reportTime = reportTime[:-3]		
				
				# Check how long iLert takes for email processing
				timediff = int(reportTime) - int(timestamp)
				print reportTime
				print timestamp
				print "ZEITDIFFERENZ - %s" % timediff
				if timediff > MAXTIMELIMIT:					
					warningtext = "Verarbeitung von Emailnotification dauerte zu lange. Dauer: %s Sekunden" % timediff
					sendWarningMail(warningtext)
					
				else:
					closeIncident(incidentID)
					closed += 1																
				
		counter += 1
	
	# if no incident was found or found incident could not be closed
	if found != closed | closed == 0:
		sendWarningMail("iLert konnte nicht alle Emailnotifications bearbeiten!")

# general email sending method
def sendMsg(mailSubject, mailTo, mailFrom, mailText):
	BODY = string.join((
        "From: %s" % mailFrom,
        "To: %s" % mailTo,
        "Subject: %s" % mailSubject ,
        "",
        mailText
        ), "\r\n")
	server = smtplib.SMTP('localhost')
	server.sendmail(mailFrom, [mailTo], BODY)
	server.quit()

# sending test messages to iLert
def sendTestMsg():	
	TO = ALARMSOURCE
	FROM = "watchdog@ilert.de"
	text = "This is a test email to ensure the functionality of the iLert server."
	sendMsg(TESTSUBJECT, TO, FROM, text)

# sending watchdog warning emails to the responsibles
def sendWarningMail(mailText):	
	TO_1 = "mcs@ilert.de"
	#TO_2 = "byz@ilert.de"
	FROM = "watchdog@ilert.de"	
	sendMsg(WARNINGSUBJECT, TO_1, FROM, mailText)
	#sendMsg(WARNINGSUBJECT, TO_2, FROM, mailText)

# wait a defined time period (seconds)
def waitSomeTime():
	time.sleep(WAITTIME)

# ----------------------------------------------------------------------
# --------------------------- main process -----------------------------
# ----------------------------------------------------------------------
#sendTestMsg()
#waitSomeTime()
xmldoc = getOpenIncidents()
checkIsMsgProcessed(xmldoc)


