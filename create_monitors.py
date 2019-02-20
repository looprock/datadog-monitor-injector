#!/usr/bin/env python
import argparse
import logging
import sys
import os
from datadog import initialize, api
import yaml


class Utils():
    def __init__(self):
        debug = os.environ.get('DEBUG', None)
        if debug:
            logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
        else:
            logging.basicConfig(stream=sys.stdout, level=logging.INFO)
        logging.getLogger('datadog.api').setLevel(logging.WARNING)
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

    def existing_monitor_names(self):
        monitor_names = {}
        all_monitors = api.Monitor.get_all()
        for monitor in all_monitors:
            monitor_names[monitor['name']] = {}
            monitor_names[monitor['name']]['id'] = monitor['id']
        return monitor_names

    def read_yaml_config(self, yaml_config):
        try:
            logging.debug(yaml_config)
            with open(yaml_config, 'r') as file_handle:
                logging.debug(type(file_handle))
                config = yaml.load(file_handle)
                return config
        except Exception as e:
            logging.error("Error while reading config file %s: %s" %
                          (yaml_config, str(e)))
            sys.exit(1)

    def find_yaml_files(self, monitor_dir):
        configs = []
        if os.path.isdir(monitor_dir):
            for root, dirs, files in os.walk(monitor_dir):
                # honestly I just put this here to get pylint to shut up
                logging.debug(dirs)
                for file in files:
                    if file.endswith(".yaml"):
                        configs.append(os.path.join(root, file))
            if not configs:
                logging.warning("No yaml files found under %s" % (monitor_dir))
        else:
                logging.info("No monitoring directory: %s" % (monitor_dir))
        return configs

    def search_monitors_directory(self):
        cwd = os.getcwd()
        monitors = "%s/monitors" % (cwd)
        return self.find_yaml_files(monitors)

    def search_infrastructure_directory(self):
        cwd = os.getcwd()
        monitors = "%s/infrastructure_monitors" % (cwd)
        return self.find_yaml_files(monitors)

    def upsert_monitor(self, config, silenced=None):
        '''A naive update that always executes, should be improved to do a diff first.'''
        if silenced:
            config['options']['silenced'] = {'*': None}
        all_existing_monitors = self.existing_monitor_names()
        logging.debug(config)
        if config['name'] in all_existing_monitors.keys():
            logging.info("*** Monitor %s is updating: %s ***" %
                         (config['name'], all_existing_monitors[config['name']]['id']))
            api.Monitor.update(
                int(all_existing_monitors[config['name']]['id']),
                type=config['type'],
                query=config['query'],
                name=config['name'],
                message=config['message'],
                tags=config['tags'],
                options=config['options']
            )
        else:
            logging.info("*** Monitor %s is creating ***" % (config['name']))
            api.Monitor.create(
                type=config['type'],
                query=config['query'],
                name=config['name'],
                message=config['message'],
                tags=config['tags'],
                options=config['options']
            )

utils = Utils()

# modes:
# look for ./monitors and process yaml files
# look for defined directory and process yaml files
# process defined yaml file
# flag to silence all alarms

parser = argparse.ArgumentParser()
parser.add_argument("-m", "--monitors", dest="monitors",
                    action="store_true", help="process a local 'monitors' directory")
parser.add_argument("-d", "--dir", dest="directory",
                    help="process comma separated list of directories", default=None)
parser.add_argument("-c", "--config", action="store", dest="config",
                    default=None, help="process comma separated list of yaml files")
parser.add_argument("-s", "--silence", action="store_true", dest="silence",
                    default=None, help="mute all monitors")
parser.add_argument("--infrastructure", action="store_true", dest="infrastructure",
                    default=None, help="Process the 'infrastructure_monitors' directory")
args = parser.parse_args()

# keeping this consistent with util.py
debug = os.environ.get('DEBUG', None)

if debug:
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
else:
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)

all_configs = []

if args.monitors:
    logging.info("## Processing monitors dir")
    all_configs = all_configs + utils.search_monitors_directory()

if args.infrastructure:
    logging.info("### Processing infrastructure_monitors dir")
    all_configs = all_configs + utils.search_infrastructure_directory()

if args.config:
    logging.info("## Processing configs: %s" % (args.config))
    tmp_configs = args.config.split(',')
    for tmp in tmp_configs:
        all_configs.append(tmp.strip())

if args.directory:
    logging.info("## Processing directories: %s" % (args.directory))
    all_dirs = []
    tmp_dirs = args.directory.split(',')
    for tmp_dir in tmp_dirs:
        logging.debug(utils.find_yaml_files(tmp_dir.strip()))
        result = utils.find_yaml_files(tmp_dir.strip())
        if result:
            logging.debug(result)
            all_dirs = all_dirs + result
        else:
            logging.warning("Found no yaml configurations in %s" %
                            (tmp_dir.strip()))
    if all_dirs:
        all_configs = all_configs + all_dirs
    else:
        logging.error("Found no yaml configs in: %s" % (args.directory))

if all_configs:
    for yaml_file in all_configs:
        logging.debug(yaml)
        if args.silence:
            utils.upsert_monitor(
                utils.read_yaml_config(yaml_file), silenced=True)
        else:
            utils.upsert_monitor(utils.read_yaml_config(yaml_file))
else:
    logging.error("No yaml files found to process!")
    sys.exit(1)
