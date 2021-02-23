import os
import logging.config
import configparser


BASE_PATH = os.path.abspath(os.path.dirname(__file__))
config = {}

logging.config.fileConfig('logging.conf')
logging.getLogger('apscheduler').setLevel(logging.WARN)

def read_config():
    config_parser = configparser.ConfigParser()
    config_file = os.path.join(BASE_PATH, 'config.ini')

    if os.path.isfile(config_file):
        config_parser.read(config_file, encoding='utf-8')

        for section in config_parser.sections():
            if section not in config:
                config[section] = dict(config_parser.items(section))


read_config()