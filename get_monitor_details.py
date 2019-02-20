#!/usr/bin/env python
import json
from datadog import initialize, api
import os
import sys
import logging
import json

debug = os.environ.get('DEBUG', None)
api_key = os.environ.get('datadog_api_key', None)
app_key = os.environ.get('datadog_app_key', None)

if not api_key:
    logging.error(
        "ERROR: no environment variable 'datadog_api_key' defined!")
    sys.exit(1)

if not app_key:
    logging.error(
        "ERROR: no environment variable 'datadog_app_key' defined!")
    sys.exit(1)

options = {
    'api_key': api_key,
    'app_key': app_key
}

initialize(**options)

deets = api.Monitor.get(sys.argv[1], group_states='all')
print(json.dumps(deets, indent=2, sort_keys=True))

# all_deets = api.Monitor.get_all()
# for monitor in all_deets:
#     print("%s %d" % (monitor['name'], monitor['id']))
