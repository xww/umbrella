import random
import time
from eventlet import greenthread
from lxml import etree
from oslo_config import cfg
from oslo_log import log as logging
from umbrella import i18n

from umbrella.virt import libvirt
from umbrella.db.sqlalchemy import api as db_api

_ = i18n._
_ = i18n._
_LE = i18n._LE
_LI = i18n._LI
_LW = i18n._LW
LOG = logging.getLogger(__name__)


class NetController(object):
    def __init__(self):
        c = libvirt.LibvirtInspector()
        self.connection = c.get_connection()

    def collect_net_info(self):
        all_domains = []
        all_domains_id = self.connection.listDomainsID()
        for domain_id in all_domains_id:
            all_domains.append(self.connection.lookupByID(domain_id))

        # all_domains_samples looks like this:
        # all_domains_samples = {'instance_uuid1': [{
        #            'instance_uuid': 'uuid',
        #            'tenant_id': 'tenant-id'
        #            'net':{'rx_bytes':100,
        #                   'tx_bytes':101,
        #                   'rx_packets':102,
        #                   'tx_packets':103},
        #             'time': 1234567889],
        #       'instance_uuid2': [{},{}]}
        all_domains_samples = {}
        for domain in all_domains:
            all_domains_samples[domain.UUIDString()] = []

        # we get vms nic info several times which equals to
        # cfg.CONF.net_task_times in total cfg.CONF.net_task_period time,
        # then we static the average value in a interval period time
        for count in range(cfg.CONF.net_task_times):
            self._get_all_domains_one_sample(all_domains, all_domains_samples)

            # before next sample, we need to sleep some time
            #greenthread.sleep(random.randint(1,
            #            cfg.CONF.net_task_period / cfg.CONF.net_task_times))
            greenthread.sleep(5)

        # statics result and write into database
        self._static_result(all_domains_samples)


    def _get_all_domains_one_sample(self, all_domains, all_domains_samples):
        for domain in all_domains:
            domain_sample = {}
            tree = etree.fromstring(domain.XMLDesc(0))
            domain_sample['instance_uuid'] = domain.UUIDString()
            domain_sample['tenant_id'] = "fake-tenant-uuid"

            nics = {}
            for iface in tree.findall('devices/interface'):
                target = iface.find('target')
                if target is not None:
                    name = target.get('dev')
                else:
                    continue;
                iface_stats = domain.interfaceStats(name)
                nics['rx_bytes'] = nics.get('rx_bytes', 0) + iface_stats[0]
                nics['rx_packets'] = nics.get('rx_packets',
                                              0) + iface_stats[1]
                nics['tx_bytes'] = nics.get('tx_bytes', 0) + iface_stats[4]
                nics['tx_packets'] = nics.get('tx_packets',
                                              0) + iface_stats[5]
                domain_sample['net'] = nics

            domain_sample['time'] = time.time()

            all_domains_samples[domain.UUIDString()].append(domain_sample)

#            # write nic info into database
#            db_api.insert_net_info(net_info)

    def _static_result(self, all_domains_samples):
        for k, samples in all_domains_samples.iteritems():
            rate_sample = {'rx_bytes_rate': [],
                           'rx_packets_rate': [],
                           'tx_bytes_rate': [],
                           'tx_packets_rate': []}

            for i in range(len(samples)-1):
                rate_sample['rx_bytes_rate'].append(int(
                    (samples[i+1]['net']['rx_bytes'] -
                     samples[i]['net']['rx_bytes']) / (
                     samples[i+1]['time'] - samples[i]['time'])) + 1)

                rate_sample['rx_packets_rate'].append(int(
                    (samples[i+1]['net']['rx_packets'] -
                     samples[i]['net']['rx_packets']) / (
                     samples[i+1]['time'] - samples[i]['time'])) + 1)

                rate_sample['tx_bytes_rate'].append(int(
                    (samples[i+1]['net']['tx_bytes'] -
                     samples[i]['net']['tx_bytes']) / (
                     samples[i+1]['time'] - samples[i]['time'])) + 1)

                rate_sample['tx_packets_rate'].append(int(
                    (samples[i+1]['net']['tx_packets'] -
                     samples[i]['net']['tx_packets']) / (
                     samples[i+1]['time'] - samples[i]['time'])) + 1)

            domain_result = {
                'rx_bytes_rate': int(sum(rate_sample[
                'rx_bytes_rate'])/len(rate_sample['rx_bytes_rate'])),
                'rx_packets_rate':int(sum(rate_sample[
                'rx_packets_rate'])/len(rate_sample['rx_packets_rate'])),
                'tx_bytes_rate':int(sum(rate_sample[
                'tx_bytes_rate'])/len(rate_sample['tx_bytes_rate'])),
                'tx_packets_rate':int(sum(rate_sample[
                'tx_packets_rate'])/len(rate_sample['tx_packets_rate'])),
            }
            domain_result['instance_uuid'] = samples[0]['instance_uuid']
            domain_result['tenant_id'] = samples[0]['tenant_id']
            LOG.info(_LI("Get instance %s net info: rx_bytes_rate: %s, "
                         "rx_packets_rate: %s, tx_bytes_rate: %s, "
                         "tx_packets_rate: %s") % (
                             domain_result['instance_uuid'],
                         domain_result['rx_bytes_rate'],
                         domain_result['rx_packets_rate'],
                         domain_result['tx_bytes_rate'],
                         domain_result['tx_packets_rate']))

            self._write_to_database(domain_result)

    def _write_to_database(self, domain_result):
        db_api.add_net_sample(domain_result)


























