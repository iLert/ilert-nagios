#!/bin/bash
# iLert Check_MK Plugin

COMMAND="/usr/local/bin/ilert_nagios.py"

$COMMAND --mode save --apikey $NOTIFY_PARAMETER_1

