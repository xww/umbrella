'''
Created on 2012-10-21

@author: hzzhoushaoyu
'''

import paste.urlmap


def root_app_factory(loader, global_conf, **local_conf):
    return paste.urlmap.urlmap_factory(loader, global_conf,
                                       **local_conf)
