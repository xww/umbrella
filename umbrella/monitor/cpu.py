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


class CpuController(object):
    def __init__(self):
        c = libvirt.LibvirtInspector()
        self.connection = c.get_connection()

    def collect_cpu_info(self):
        all_domains = []
        all_domains_id = self.connection.listDomainsID()
        for domain_id in all_domains_id:
            all_domains.append(self.connection.lookupByID(domain_id))

        # all_domains_samples looks like this:
        # all_domains_samples = {'instance_uuid1': [{
        #            'instance_uuid': 'uuid',
        #            'tenant_id': 'tenant-id'
        #            'cpu':{'cpu_load':0.85}        #
        #            'time': 1234567889],
        #         'instance_uuid2': [{},{}]}
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
            domain_sample['instance_uuid'] = domain.UUIDString()
            domain_sample['tenant_id'] = "fake-tenant-uuid"

            cpu = {"cpu_time": domain.info()[4]}
            domain_sample['cpu'] = cpu
            domain_sample['time'] = time.time()
            all_domains_samples[domain.UUIDString()].append(domain_sample)


    def _static_result(self, all_domains_samples):
        for k, samples in all_domains_samples.iteritems():
            cpu_load_sample = {'cpu_load': []}

            for i in range(len(samples)-1):
                load = (samples[i+1]['cpu']['cpu_time'] -
                        samples[i]['cpu']['cpu_time'])/(
                        samples[i+1]['time'] - samples[i]['time'])
                load = round(load/pow(10, 9), 2) * 100
                cpu_load_sample['cpu_load'].append(load)


            domain_result = {
                'cpu_load': int(sum(cpu_load_sample[
                'cpu_load'])/len(cpu_load_sample['cpu_load'])),
            }
            domain_result['instance_uuid'] = samples[0]['instance_uuid']
            domain_result['tenant_id'] = samples[0]['tenant_id']
            LOG.info(_LI("Get instance %s cpu info: cpu_time: %s, ") % (
                             domain_result['instance_uuid'],
                         domain_result['cpu_load']))

            self._write_to_database(domain_result)

    def _write_to_database(self, domain_result):
        db_api.add_cpu_sample(domain_result)

