'''
Created on 2012-10-21

@author: hzzhoushaoyu
'''

from umbrella.common import cfg
from umbrella.common import importutils

sql_connection_opt = cfg.StrOpt('sql_connection',
                                default='sqlite:///umbrella.sqlite',
                                secret=True,
                                metavar='CONNECTION',
                                help='A valid SQLAlchemy connection '
                                     'string for the registry database. '
                                     'Default: %default')

CONF = cfg.CONF
CONF.register_opt(sql_connection_opt)


def add_cli_options():
    """
    Adds any configuration options that the db layer might have.

    :retval None
    """
    CONF.unregister_opt(sql_connection_opt)
    CONF.register_cli_opt(sql_connection_opt)


def get_api():
    return importutils.import_module(CONF.data_api)

# attributes common to all models
BASE_MODEL_ATTRS = set(['id', 'created_at', 'updated_at', 'deleted_at',
                        'deleted'])


SETTING_ATTRS = BASE_MODEL_ATTRS | set(['uuid', 'level', 'type', 'capacity',
                        'threshold', 'alarm_title', 'alarm_content', 'enable'])
ALARM_ATTRS = BASE_MODEL_ATTRS | set(['settings_uuid', 'usage', 'done',
                                      'readed', 'read_user_id', 'setting'])
