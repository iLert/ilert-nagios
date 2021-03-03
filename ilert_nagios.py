#!/usr/bin/env python


# iLert Nagios/Icinga/Check_MK Plugin
#
# Copyright (c) 2013-2020, iLert GmbH. <support@ilert.com>
# All rights reserved.


import os
import syslog
import fcntl
import urllib2
from urllib2 import HTTPError
from urllib2 import URLError
import uuid
import ssl
from xml.sax.saxutils import escape
from xml.sax.saxutils import quoteattr
import argparse
import io

PLUGIN_VERSION = "1.4"


def persist_event(api_key, directory, payload):
    """Persists event to disk"""
    syslog.syslog('writing event to disk...')

    xml_doc = create_xml(api_key, payload)

    uid = uuid.uuid4()

    filename = "%s.ilert" % uid
    filename_tmp = "%s.tmp" % uid
    file_path = "%s/%s" % (directory, filename)
    file_path_tmp = "%s/%s" % (directory, filename_tmp)

    try:
        # atomic write using tmp file, see http://stackoverflow.com/questions/2333872
        with io.open(file_path_tmp, mode="w", encoding="utf-8") as f:
            f.write(xml_doc)
            # make sure all data is on disk
            f.flush()
            # skip os.sync in favor of performance/responsiveness
            # os.fsync(f.fileno())
            f.close()
            os.rename(file_path_tmp, file_path)
            syslog.syslog('created event file in %s' % file_path)
    except Exception as e:
        syslog.syslog(syslog.LOG_ERR, "could not write event to %s. Cause: %s %s" % (file_path, type(e), e.args))
        exit(1)


def lock_and_flush(endpoint, directory, port, insecure):
    """Lock event directory and call flush"""
    lock_filename = "%s/lockfile" % directory

    lockfile = open(lock_filename, "w")

    try:
        fcntl.flock(lockfile.fileno(), fcntl.LOCK_EX)
        flush(endpoint, directory, port, insecure)
    finally:
        lockfile.close()


def flush(endpoint, directory, port, insecure):
    """Send all events in event directory to iLert"""
    headers = {"Content-type": "application/xml", "Accept": "application/xml"}
    url = "%s:%s/api/v1/events/nagios" % (endpoint, port)

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
            ctx = ssl.create_default_context()
            if insecure == True:
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
            req = urllib2.Request(url, xml_doc, headers)
            urllib2.urlopen(req, timeout=60, context=ctx)
        except HTTPError as e:
            if e.code == 429:
                syslog.syslog(syslog.LOG_WARNING, "too many requests, will try later. Server response: %s" % e.read())
            elif 400 <= e.code <= 499:
                syslog.syslog(syslog.LOG_WARNING, "event not accepted by iLert. Reason: %s" % e.read())
                os.remove(event)
            else:
                syslog.syslog(syslog.LOG_ERR,
                              "could not send event to iLert. HTTP error code %s, reason: %s, %s" % (
                                  e.code, e.reason, e.read()))
        except URLError as e:
            syslog.syslog(syslog.LOG_ERR, "could not send event to iLert. Reason: %s" % e.reason)
        except Exception as e:
            syslog.syslog(syslog.LOG_ERR,
                          "an unexpected error occurred. Please report a bug. Cause: %s %s" % (type(e), e.args))
        else:
            os.remove(event)
            syslog.syslog('event %s has been sent to iLert and removed from event directory' % event)


def create_xml(apikey, payload):
    """Create event xml using the provided api key and event payload"""
    xml_doc = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    xml_doc += "<event><apiKey>%s</apiKey><payload>" % apikey

    for entry in payload:
        xml_doc += "<entry key=%s>%s</entry>" % (quoteattr(entry), unicode(escape(payload[entry]), encoding='utf-8', errors='ignore'))

    # XML document end tag
    xml_doc += "</payload></event>"

    return xml_doc


def main():
    parser = argparse.ArgumentParser(description='send events from Nagios (and its forks, such as Icinga) to iLert')
    parser.add_argument('-m', '--mode', choices=['nagios', 'save', 'cron', 'send'], required=True,
                        help='Execution mode: "save" persists an event to disk and "send" submits all saved events '
                             'to iLert. Note that after every "save" "send" will also be called.')
    parser.add_argument('-a', '--apikey', help='API key for the alert source in iLert')
    parser.add_argument('-e', '--endpoint', default='https://ilertnow.com',
                        help='iLert API endpoint (default: %(default)s)')
    parser.add_argument('-p', '--port', type=int, default=443, help='Endpoint port (default: %(default)s)')
    parser.add_argument('-d', '--dir', default='/tmp/ilert_nagios',
                        help='Event directory where events are stored (default: %(default)s)')
    parser.add_argument('--version', action='version', version=PLUGIN_VERSION)
    parser.add_argument('-k', '--insecure', type=bool, default=False,
                        help='Allow insecure server connections when using SSL (default: %(default)s)')
    parser.add_argument('-x', '--proxy', help='Use proxy for the outbound traffic')
    parser.add_argument('payload', nargs=argparse.REMAINDER,
                        help='Event payload as key value pairs in the format key1=value1 key2=value2 ...')
    args = parser.parse_args()

    # populate payload data from environment variables
    payload = dict(PLUGIN_VERSION=PLUGIN_VERSION)
    for env in os.environ:
        if "NAGIOS_" in env or "ICINGA_" in env or "NOTIFY_" in env:
            payload[env] = os.environ[env]

    # ... and payload specified via command line
    payload.update([arg.split('=', 1) for arg in args.payload])

    if args.apikey is not None:
        apikey = args.apikey
    elif 'NAGIOS_CONTACTPAGER' in payload:
        apikey = payload['NAGIOS_CONTACTPAGER']
    elif 'ICINGA_CONTACTPAGER' in payload:
        apikey = payload['ICINGA_CONTACTPAGER']
    elif 'CONTACTPAGER' in payload:
        apikey = payload['CONTACTPAGER']
    else:
        apikey = None

    if not os.path.exists(args.dir):
        os.makedirs(args.dir)

    if args.proxy is not None:
        os.environ['http_proxy'] = args.proxy
        os.environ['https_proxy'] = args.proxy

    if args.mode == "nagios" or args.mode == "save":
        if apikey is None:
            error_msg = "parameter apikey is required in save mode and must be provided either via command line or in " \
                        "the pager field of the contact definition in Nagios/Icinga"
            syslog.syslog(syslog.LOG_ERR, error_msg)
            parser.error(error_msg)
        persist_event(apikey, args.dir, payload)
        lock_and_flush(args.endpoint, args.dir, args.port, args.insecure)
    elif args.mode == "cron" or args.mode == "send":
        lock_and_flush(args.endpoint, args.dir, args.port, args.insecure)

    exit(0)


if __name__ == '__main__':
    main()
