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


class DiskController(object):
    def __init__(self):
        c = libvirt.LibvirtInspector()
        self.connection = c.get_connection()

    def collect_disk_info(self):
        all_domains = []
        all_domains_id = self.connection.listDomainsID()
        for domain_id in all_domains_id:
            all_domains.append(self.connection.lookupByID(domain_id))

        # all_domains_samples looks like this:
        # all_domains_samples = {'instance_uuid1': [{
        #            'instance_uuid': 'uuid',
        #            'tenant_id': 'tenant-id'
        #            'disk':{'rd_req':100,
        #                   'rd_bytes':101,
        #                   'wr_req':102,
        #                   'wr_bytes':103},
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
            #greenthread.sleep(random.randint(1,cfg.CONF.net_task_period / cfg.CONF.net_task_times))
            greenthread.sleep(5)

        # statics result and write into database
        self._static_result(all_domains_samples)


    def _get_all_domains_one_sample(self, all_domains, all_domains_samples):
        for domain in all_domains:
            domain_sample = {}
            tree = etree.fromstring(domain.XMLDesc(0))
            domain_sample['instance_uuid'] = domain.UUIDString()
            domain_sample['tenant_id'] = "fake-tenant-uuid"

            disks = {}
            for device in filter(bool, [target.get(
                "dev") for target in tree.findall('devices/disk/target')]):
                block_stats = domain.blockStats(device)

                disks['rd_req'] = disks.get('rd_req', 0) + block_stats[0]
                disks['rd_bytes'] = disks.get('rd_bytes', 0) + block_stats[1]
                disks['wr_req'] = disks.get('wr_req', 0) + block_stats[2]
                disks['wr_bytes'] = disks.get('wr_bytes', 0) + block_stats[3]

                domain_sample['disk'] = disks

            domain_sample['time'] = time.time()

            all_domains_samples[domain.UUIDString()].append(domain_sample)


    def _static_result(self, all_domains_samples):
        for k, samples in all_domains_samples.iteritems():
            rate_sample = {'rd_req_rate': [],
                           'rd_bytes_rate': [],
                           'wr_req_rate': [],
                           'wr_bytes_rate': []}

            for i in range(len(samples)-1):
                rate_sample['rd_req_rate'].append(int(
                    (samples[i+1]['disk']['rd_req'] -
                     samples[i]['disk']['rd_req']) / (
                     samples[i+1]['time'] - samples[i]['time'])))

                rate_sample['rd_bytes_rate'].append(int(
                    (samples[i+1]['disk']['rd_bytes'] -
                     samples[i]['disk']['rd_bytes']) / (
                     samples[i+1]['time'] - samples[i]['time'])))

                rate_sample['wr_req_rate'].append(int(
                    (samples[i+1]['disk']['wr_req'] -
                     samples[i]['disk']['wr_req']) / (
                     samples[i+1]['time'] - samples[i]['time'])))

                rate_sample['wr_bytes_rate'].append(int(
                    (samples[i+1]['disk']['wr_bytes'] -
                     samples[i]['disk']['wr_bytes']) / (
                     samples[i+1]['time'] - samples[i]['time'])))

            domain_result = {
                'rd_req_rate': int(sum(rate_sample[
                'rd_req_rate'])/len(rate_sample['rd_req_rate'])),
                'rd_bytes_rate':int(sum(rate_sample[
                'rd_bytes_rate'])/len(rate_sample['rd_bytes_rate'])),
                'wr_req_rate':int(sum(rate_sample[
                'wr_req_rate'])/len(rate_sample['wr_req_rate'])),
                'wr_bytes_rate':int(sum(rate_sample[
                'wr_bytes_rate'])/len(rate_sample['wr_bytes_rate'])),
            }
            domain_result['instance_uuid'] = samples[0]['instance_uuid']
            domain_result['tenant_id'] = samples[0]['tenant_id']
            LOG.info(_LI("Get instance %s disk info: rd_req_rate: %s, "
                         "rd_bytes_rate: %s, wr_req_rate: %s, "
                         "wr_bytes_rate: %s") % (
                             domain_result['instance_uuid'],
                         domain_result['rd_req_rate'],
                         domain_result['rd_bytes_rate'],
                         domain_result['wr_req_rate'],
                         domain_result['wr_bytes_rate']))

            self._write_to_database(domain_result)

    def _write_to_database(self, domain_result):
        db_api.add_disk_sample(domain_result)


























