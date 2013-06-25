#!/usr/bin/env python


# iLert Nagios Plugin
#
# Copyright (c) 2013, iLert UG. <info@ilert.de>
# All rights reserved.


import os, sys, uuid, syslog, fcntl, httplib
from optparse import OptionParser


def persist_event(apikey, directory):
    """Persists nagios event to disk"""
    syslog.syslog('writing event to disk...')

    xmldoc = create_xml(apikey)
    
    # Old UUID
    # oneUuid = uuid.uuid4()
    
    # New UUID
    oneUuid = int(time.time()*100000)

    filename = "%d.ilert" % oneUuid
    filename_tmp = "%d.tmp" % oneUuid
    file_path = "%s/%s" % (directory, filename)
    file_path_tmp = "%s/%s" % (directory, filename_tmp)

    try:
        # atomic write using tmp file, see http://stackoverflow.com/questions/2333872
        f = open(file_path_tmp, "w")
        f.write(xmldoc)
        # make sure all data is on disk
        f.flush()
        # skip os.sync in favor of performance/responsiveness
        #os.fsync(f.fileno())
        f.close()
        os.rename(file_path_tmp, file_path)
        syslog.syslog('created a nagios event in %s' % file_path)
    except Exception as e:
        syslog.syslog(syslog.LOG_ERR, "could not write nagios event to %s. Cause: %s %s" % (file_path, type(e), e.args))
        exit(1)
    finally:
        f.close()


def lock_and_flush(host, directory, port):
    """Lock event directory and call flush"""
    lock_filename = "%s/lockfile" % directory

    lockfile = open(lock_filename, "w")

    try:
        fcntl.flock(lockfile.fileno(), fcntl.LOCK_EX)
        flush(host, directory, port)
    finally:
        lockfile.close()


def flush(host, directory, port):
    """Send all events in event directory to iLert"""
    syslog.syslog('sending nagios events to iLert...')

    eventList = os.listdir(directory)
    eventList.sort()

    for event in eventList:
        if event.endswith(".ilert"):
            file_name = "%s/%s" % (directory, event)

            xmldoc = ""
            try:
                f = open(file_name, "r")
                for line in f:
                    xmldoc += line
            except IOError:
                continue
            finally:
                f.close()

            syslog.syslog('sending event %s to ilert...' % event)
            s_result = send(host, port, xmldoc)

            if s_result == 0:
                os.remove(file_name)
                syslog.syslog('event %s has been sent to iLert and removed from event directory' % event)
            else:
                syslog.syslog(syslog.LOG_ERR, 'sending event %s failed' % event)


def create_xml(apikey):
    """Create incident xml content with nagios macros provided via environment variables"""

    xmldoc = "<event><apiKey>%s</apiKey><payload>" % apikey

    # read NAGIOS macros from environment variables
    for env in os.environ:
        if "NAGIOS_" in env:
            xmldoc += "<entry key=\"%s\">%s</entry>" % (env, os.environ[env])

    xmldoc += "<entry key=\"%s\">%s</entry>" % ("PLUGIN_VERSION", "1.0")

    # XML document end tag
    xmldoc += "</payload></event>"

    return xmldoc


def send(host, port, xmldoc):
    """Send event to iLert"""
    headers = {"Content-type": "application/xml", "Accept": "application/xml"}
    data = "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"

    data += xmldoc

    try:
        syslog.syslog('connecting to iLert at host %s and port %s...' % (host, port))
        conn = httplib.HTTPConnection(host, port, timeout=60)
        conn.request("POST", "/rest/events", data, headers)
        response = conn.getresponse()

        if (response.status == "200") or (response.reason == "OK"):
            return 0
        else:
            syslog.syslog(syslog.LOG_ERR, "could not send nagios event to iLert. Status: %s, reason: %s" % (response.status, response.reason))
            return 1
    except Exception as e:
        syslog.syslog(syslog.LOG_ERR, "could not send nagios event to iLert. Cause: %s %s" % (type(e), e.args))
        return 1
    finally:
        conn.close()


def main():
    # Define nagios plugin options
    parser = OptionParser("ilert_nagios.py -m {nagios|cron} [-a apikey] [-i iLertHost] [-p Port] [-d eventDir]")
    parser.add_option("-m", "--mode", dest="mode", help="Execution mode [nagios|cron]")
    parser.add_option("-a", "--apikey", dest="apikey", help="(optional) API-Key for the iLert account")
    parser.add_option("-i", "--iLerthost", dest="host", help="(optional) iLert host - default is ilertnow.com")
    parser.add_option("-p", "--port", dest="port", help="(optional) host port - default port is 80")
    parser.add_option("-d", "--dir", dest="directory", help="(optional) event directory where incidents are stored")
    (options, args) = parser.parse_args()

    # required parameters
    if options.mode is not None:
        mode = options.mode
    else:
        parser.error('missing required mode parameter.')

    # optional parameters
    if options.directory is not None:
        directory = options.directory
    else:
        directory = "/tmp/ilert_nagios"

    if options.apikey is not None:
        apikey = options.apikey
    elif 'NAGIOS_CONTACTPAGER' in os.environ:
        apikey = os.environ['NAGIOS_CONTACTPAGER']

    if options.host is not None:
        host = options.host
    else:
        host = "ilertnow.com"

    try:
        if options.port is not None:
            port = int(options.port)
            if port < 0 or port > 65535:
                raise ValueError('Invalid port')
        else:
            port = 80

    except ValueError as e:
        print type(e)
        print e.args
        print "The port parameter has to be a number between 0 and 65535."
        sys.exit()

    if not os.path.exists(directory):
        os.makedirs(directory)

    if mode == "nagios":		
        persist_event(apikey, directory)
        lock_and_flush(host, directory, port)
    elif mode == "cron":		
        lock_and_flush(host, directory, port)
    else:
        parser.error("The iLert nagios plugin mode is not defined.")

    exit(0)


if __name__ == '__main__':
    main()
