#!/usr/bin/env python


# iLert Nagios/Icinga Plugin
#
# Copyright (c) 2013-2015, iLert UG. <info@ilert.de>
# All rights reserved.


import os
import syslog
import fcntl
import urllib2
from urllib2 import HTTPError
from urllib2 import URLError
import uuid
from xml.sax.saxutils import escape
from xml.sax.saxutils import quoteattr
from optparse import OptionParser

PLUGIN_VERSION = "1.1"


def persist_event(api_key, directory):
    """Persists nagios event to disk"""
    syslog.syslog('writing event to disk...')

    xml_doc = create_xml(api_key)

    uid = uuid.uuid4()

    filename = "%s.ilert" % uid
    filename_tmp = "%s.tmp" % uid
    file_path = "%s/%s" % (directory, filename)
    file_path_tmp = "%s/%s" % (directory, filename_tmp)

    try:
        # atomic write using tmp file, see http://stackoverflow.com/questions/2333872
        f = open(file_path_tmp, "w")
        f.write(xml_doc)
        # make sure all data is on disk
        f.flush()
        # skip os.sync in favor of performance/responsiveness
        # os.fsync(f.fileno())
        f.close()
        os.rename(file_path_tmp, file_path)
        syslog.syslog('created nagios event file in %s' % file_path)
    except Exception as e:
        syslog.syslog(syslog.LOG_ERR, "could not write nagios event to %s. Cause: %s %s" % (file_path, type(e), e.args))
        exit(1)
    finally:
        f.close()


def lock_and_flush(endpoint, directory, port):
    """Lock event directory and call flush"""
    lock_filename = "%s/lockfile" % directory

    lockfile = open(lock_filename, "w")

    try:
        fcntl.flock(lockfile.fileno(), fcntl.LOCK_EX)
        flush(endpoint, directory, port)
    finally:
        lockfile.close()


def flush(endpoint, directory, port):
    """Send all events in event directory to iLert"""
    headers = {"Content-type": "application/xml", "Accept": "application/xml"}
    url = "%s:%s/rest/events" % (endpoint, port)

    # populate list of event files sorted by creation date
    events = [os.path.join(directory, f) for f in os.listdir(directory)]
    events = filter(lambda x: x.endswith(".ilert"), events)
    events.sort(key=lambda x: os.path.getmtime(x))

    for event in events:
        try:
            with open(event, 'r') as f:
                xml_doc = f.read()
        except IOError:
            continue

        syslog.syslog('sending event %s to iLert...' % event)

        try:
            req = urllib2.Request(url, xml_doc, headers)
            urllib2.urlopen(req, timeout=60)
        except HTTPError as e:
            if e.code == 400:
                syslog.syslog(syslog.LOG_WARNING, "event not accepted by iLert. Reason: %s" % e.read())
                os.remove(event)
            else:
                syslog.syslog(syslog.LOG_ERR,
                              "could not send nagios event to iLert. HTTP error code %s, reason: %s, %s" % (
                                  e.code, e.reason, e.read()))
        except URLError as e:
            syslog.syslog(syslog.LOG_ERR, "could not send nagios event to iLert. Reason: %s" % e.reason)
        except Exception as e:
            syslog.syslog(syslog.LOG_ERR,
                          "an unexpected error occurred. Please report a bug. Cause: %s %s" % (type(e), e.args))
        else:
            os.remove(event)
            syslog.syslog('event %s has been sent to iLert and removed from event directory' % event)


def create_xml(apikey):
    """Create incident xml content with nagios or icinga macros provided via environment variables"""
    xml_doc = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    xml_doc += "<event><apiKey>%s</apiKey><payload>" % apikey

    # read NAGIOS/ICINGA macros from environment variables
    for env in os.environ:
        if "NAGIOS_" in env or "ICINGA_" in env:
            xml_doc += "<entry key=%s>%s</entry>" % (quoteattr(env), escape(os.environ[env]))

    xml_doc += '<entry key="%s">%s</entry>' % ("PLUGIN_VERSION", PLUGIN_VERSION)

    # XML document end tag
    xml_doc += "</payload></event>"

    return xml_doc


def main():
    # Define nagios plugin options
    parser = OptionParser("ilert_nagios.py -m {nagios|cron} [-a apikey] [-e endpoint] [-p port] [-d eventDir]")
    parser.add_option("-m", "--mode", dest="mode", help="Execution mode [nagios|cron]")
    parser.add_option("-a", "--apikey", dest="apikey", help="(optional) API key for the alert source in iLert")
    parser.add_option("-e", "--endpoint", dest="endpoint",
                      help="(optional) iLert API endpoint - default is https://ilertnow.com")
    parser.add_option("-p", "--port", dest="port", help="(optional) endpoint port - default port is 443")
    parser.add_option("-d", "--dir", dest="directory",
                      help="(optional) event directory where incidents are stored - default is /tmp/ilert_nagios")
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
    elif 'ICINGA_CONTACTPAGER' in os.environ:
        apikey = os.environ['ICINGA_CONTACTPAGER']
    else:
        apikey = None

    if options.endpoint is not None:
        endpoint = options.endpoint
    else:
        endpoint = "https://ilertnow.com"

    if options.port is not None:
        try:
            port = int(options.port)
        except ValueError:
            port = -1
        if port < 0 or port > 65535:
            syslog.syslog(syslog.LOG_ERR, 'invalid port number: %s, must be between 0 and 65535' % port)
            exit(1)
    else:
        port = 443

    if not os.path.exists(directory):
        os.makedirs(directory)

    if mode == "nagios":
        if apikey is None:
            error_msg = "parameter apikey is required in nagios mode and must be provided either via command line or in " \
                        "the pager field of the contact definition in Nagios/Icinga"
            syslog.syslog(syslog.LOG_ERR, error_msg)
            parser.error(error_msg)
        persist_event(apikey, directory)
        lock_and_flush(endpoint, directory, port)
    elif mode == "cron":
        lock_and_flush(endpoint, directory, port)
    else:
        parser.error('invalid mode parameter %s' % mode)

    exit(0)


if __name__ == '__main__':
    main()
