# Copyright 2011 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
Various conveniences used for migration scripts
"""

from oslo_log import log as logging
import sqlalchemy.types

from umbrella import i18n


LOG = logging.getLogger(__name__)
_LI = i18n._LI


String = lambda length: sqlalchemy.types.String(
    length=length, convert_unicode=False,
    unicode_error=None, _warn_on_bytestring=False)


Text = lambda: sqlalchemy.types.Text(
    length=None, convert_unicode=False,
    unicode_error=None, _warn_on_bytestring=False)


Boolean = lambda: sqlalchemy.types.Boolean(create_constraint=True, name=None)


DateTime = lambda: sqlalchemy.types.DateTime(timezone=False)


Integer = lambda: sqlalchemy.types.Integer()


BigInteger = lambda: sqlalchemy.types.BigInteger()


PickleType = lambda: sqlalchemy.types.PickleType()


Numeric = lambda: sqlalchemy.types.Numeric()


def from_migration_import(module_name, fromlist):
    module_path = \
            'umbrella.db.sqlalchemy.migrate_repo.versions.%s' % module_name
    module = __import__(module_path, globals(), locals(), fromlist, 0)
    return [getattr(module, item) for item in fromlist]


def create_tables(tables):
    for table in tables:
        LOG.info(_LI("creating table %(table)s") % {'table': table})
        table.create()


def drop_tables(tables):
    for table in tables:
        LOG.info(_LI("dropping table %(table)s") % {'table': table})
        table.drop()
