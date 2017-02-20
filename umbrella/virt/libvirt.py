from lxml import etree
from oslo_config import cfg
from oslo_utils import units
import six

from umbrella.i18n import _
#from umbrella.common import log as logging
from oslo_log import log as logging

Connection = None
Libvirt = None

LOG = logging.getLogger(__name__)

OPTS = [
    cfg.StrOpt('libvirt_type',
                default='kvm',
                choices=['kvm', 'lxc', 'qemu', 'uml', 'xen'],
                help='Libvirt domain type.'),
    cfg.StrOpt('libvirt_uri',
                default='qemu:///system',
                help='Override the default libvirt URI '
                 '(which is dependent on libvirt_type).'),
]

CONF = cfg.CONF
CONF.register_opts(OPTS)

def retry_on_disconnect(function):
    def decorator(self, *args, **kwargs):
        try:
            return function(self, *args, **kwargs)
        except libvirt.libvirtError as e:
            if (e.get_error_code() == libvirt.VIR_ERR_SYSTEM_ERROR and
                e.get_error_domain() in (libvirt.VIR_FROM_REMOTE,
                                         libvirt.VIR_FROM_RPC)):
                LOG.debug(_('Connection to libvirt broken'))
                self.connection = None
                return function(self, *args, **kwargs)
            else:
                raise
    return decorator

class LibvirtInspector(object):
    def __init__(self):
        self.uri = self._get_uri()
        #global connection
        self.connection = Connection

    def _get_uri(self):
        return CONF.libvirt_uri

    def get_connection(self):
        if not self.connection:
            global Libvirt
            if Libvirt is None:
                Libvirt = __import__('libvirt')

            global Connection
            if Connection is None:
                Connection = Libvirt.openReadOnly(self.uri)
                self.connection = Connection
                LOG.debug(_('create a new connection to libvirt: %s'), self.uri)
        return self.connection

    @retry_on_disconnect
    def lookup_by_uuid(self, instance_uuid):
        try:
            return self.get_connection().lookupByUUIDString(instance.id)
        except Exception as ex:
            if not libvirt or not isinstance(ex, libvirt.libvirtError):
                raise ex
            error_code = ex.get_error_code()
            if (error_code == libvirt.VIR_ERR_SYSTEM_ERROR and
                ex.get_error_domain() in (libvirt.VIR_FROM_REMOTE,
                                          libvirt.VIR_FROM_RPC)):
                raise
            msg = _("Error from libvirt while looking up instance "
                    "<instance_uuidid=%(id)s>: " % instance_uuid)
            raise virt_inspector.InstanceNotFoundException(msg)

    #def inspect_cpus(self, instance_uuid):
    #    domain = self.lookup_by_uuid(instance_uuid)
    #    dom_info = domain.info()
    #    return virt_inspector.CPUStats(number=dom_info[3], time=dom_info[4])























