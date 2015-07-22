'''
Created on 2012-10-24

@author: hzzhoushaoyu
'''

from umbrella.api.list_operation import filter
from umbrella.api.list_operation import sort
from umbrella.common import wsgi
from umbrella.common import cfg
from umbrella.common import utils
from umbrella.openstack import client
from umbrella.openstack import api
import umbrella.common.log as logging

CONF = cfg.CONF

LOG = logging.getLogger(__name__)
IMAGE_REMOVE_PROPERTIES = ["each_time_info", "image_total_info"]

opts = [
        cfg.IntOpt('image_api_limit', default=1000)
        ]
CONF.register_opts(opts)


class Controller(object):

    def _glance_request(self, req):
        c = client.GlanceClient()
        result, headers = c.request(req)
        return result, headers

    def _get_image(self, req, image, image_type=None):
        '''
        get more info for single image.
        '''
        if image_type == 'image' and \
                'image_type' in image.get('properties', {}) and \
                image.get('properties').get('image_type') == 'snapshot':
            return None
        elif image_type == 'snapshot' and \
                'image_type' not in image.get('properties', {}):
            return None
        image_owner_id = image['owner']
        auth_token = req.context.auth_tok
        tenant = api.get_tenant(image_owner_id, auth_token)
        tenant_name = tenant['name']
        image['owner_name'] = tenant_name
        return image

    def _get_images(self, req):
        '''
        list all images support querying only image
        if query property-image_type=image, get all images and snapshots,
        and then remove snapshots from images.
        '''
        params = req.params.mixed()
        c = client.GlanceClient()
        result_list = []
        image_type = params.get('property-image_type')
        if image_type is not None and \
                    image_type == 'image':
            # abandon which is not snapshot
            # get all images
            params.pop("property-image_type")
        # update list limit
        params.update(limit=CONF.image_api_limit)
        result, headers = c.response(req.method, req.path, params=params,
                         headers=req.headers, body=req.body)
        for image in result['images']:
            target = self._get_image(req, image, image_type)
            if target is not None:
                result_list.append(target)
        return dict(images=result_list)

    @utils.log_func_exe_time
    def index(self, req):
        '''
        list all images or snapshots
        support filters by property-xx and owner
        support sort by sort_key and sort_dir
        '''
        result = self._get_images(req)
        result = filter.filter_images(req, result['images'])
        result = sort.sort_images(req, result)
        return dict(images=result)

    def show(self, req, image_id):
        '''
        show image info by specified image id
        '''
        result, headers = self._glance_request(req)
        temp = None
        for k, v in headers:
            if k == 'x-image-meta-owner':
                auth_token = req.context.auth_tok
                tenant = api.get_tenant(v, auth_token)
                temp = ('x-image-meta-owner_name', tenant['name'])
        if temp is not None:
            headers.append(temp)
        return headers

    def delete(self, req, image_id):
        '''
        delete image by specified image id
        '''
        result, headers = self._glance_request(req)
        return result

    def update(self, req, image_id, body=None):
        '''
        update image attributes by specified image id
        '''
        result, headers = self._glance_request(req)
        return result


class ImageSerialize(wsgi.JSONResponseSerializer):

    def index(self, response, images):
        for image in images['images']:
            properties_dict = filter_image_properties(image['properties'])
            for property_key in properties_dict:
                image["property-%s" % property_key] = \
                                properties_dict[property_key]
            image.pop("properties")
        response.body = self.to_json(images)
        response.content_type = 'application/json'

    def show(self, response, image_metas):
        properties_dict = dict((k, v) for k, v in image_metas)
        properties_dict = filter_image_properties(properties_dict)
        response.headers.update(properties_dict)


def filter_image_properties(image_metas_dict):
    result = {}
    # FIXME(hzzhoushaoyu): should not pop dict in iterator.
    # So, how to remove properties in dict in simple way.
    for key in image_metas_dict:
        need_remove = False
        for remove_prop in IMAGE_REMOVE_PROPERTIES:
            if remove_prop in key:
                need_remove = True
                break
        if not need_remove:
            result.update({key: image_metas_dict[key]})
    return result


def create_resource():
    """Servers resource factory method"""
    return wsgi.Resource(Controller(), serializer=ImageSerialize())
