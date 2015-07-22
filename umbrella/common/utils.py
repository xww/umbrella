# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
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
System-level utilities and helper functions.
"""

import errno

try:
    from eventlet import sleep
except ImportError:
    from time import sleep
from eventlet import greenthread
from eventlet import event

import functools
import inspect
import os
import platform
import subprocess
import sys
import time
import uuid

from webob import exc

from umbrella.common import exception
import umbrella.common.log as logging


LOG = logging.getLogger(__name__)


def get_support_keys(search_opts={}, support_params={}):
    values = {}
    for params in support_params:
        if params in search_opts:
            values[params] = search_opts[params]
    return values


def mb_to_gb(result):
    return round((float(result) / 1024), 2)


def convert_mem_to_gb_for_monitor(result):
    # Note(hzrandd): Depend on the different  levels,
    #convert the memory unit from MB to GB for monitor.
    #level info: PLATFORM_LEVEL = 0, HOST_LEVEL = 1
    #USER_LEVEL = 2, AZ_LEVEL = 3

    for k in result:
        if k['metricName'].endswith('_mb'):
            k['value'] = mb_to_gb(k['value'])
            k['metricName'] = k['metricName'].rstrip('_mb') + '_gb'


def _convert_mb_info_to_gb(result):
    for re in result:
        if 'memory_mb' == re['name']:
            re['name'] = 'memory_gb'
            for k in re['values']:
                k['currentValue'] = mb_to_gb(k['currentValue'])
                if k['description'].endswith('mb'):
                    k['description'] = \
                        k['description'].rstrip('mb') + 'gb'
                if k['metricName'].endswith('mb'):
                    k['metricName'] = \
                        k['metricName'].rstrip('mb') + 'gb'
    return result


def convert_mem_from_mb_to_gb(f):
   #Note(hzrandd): modfiy the memory unit and description from mb to gb
    def wrapper(*args, **kwargs):
        if f.__name__ == 'index':
            result = f(*args, **kwargs)
            for k, v in result['memory_mb'].iteritems():
                result['memory_mb'][k] = mb_to_gb(v)
            result.update(memory_gb=result.pop('memory_mb'))
            return result

        if f.__name__ == 'list_platform_usage':
            result = f(*args, **kwargs)
            return _convert_mb_info_to_gb(result)

        if f.__name__ == 'list_az_usage':
            result = f(*args, **kwargs)
            return _convert_mb_info_to_gb(result)

        if f.__name__ == 'show_by_host':
            result = f(*args, **kwargs)
            for k in result['hosts']:
                if 'memory_mb' in k:
                    k['memory_mb'] = mb_to_gb(k['memory_mb'])
                    k.update(memory_gb=k.pop('memory_mb'))
                    if 'memory_mb_used' in k:
                        k['memory_mb_used'] = \
                            mb_to_gb(k['memory_mb_used'])
                        k.update(memory_gb_used=k.pop('memory_mb_used'))
            return result

        if f.__name__ == 'show_by_tenant':
            result = f(*args, **kwargs)
            for k in result['tenants']:
                if 'memory_mb_used' in k:
                    k['memory_mb_used'] = \
                        mb_to_gb(k['memory_mb_used'])
                    k.update(memory_gb_used=k.pop('memory_mb_used'))
            return result

        if f.__name__ == 'list_all_quotas':
            result = f(*args, **kwargs)
            for rams in result['quotas']:
                for k, v in rams['ram'].iteritems():
                    rams['ram'][k] = mb_to_gb(v)
            return result

        if f.__name__ == 'list_quotas':
            result = f(*args, **kwargs)
            result['quota_set']['ram'] = mb_to_gb(result['quota_set']['ram'])
            return result

    return wrapper


def is_admin_context(context):
    """Indicates if the request context is an administrator."""
    if not context:
        raise Exception('Use of empty request context is deprecated')
    return context.is_admin


def require_admin_context(f):
    def wrapper(*args, **kwargs):
        if not args[1] or not is_admin_context(args[1].context):
            raise exception.AdminRequired()
        return f(*args, **kwargs)
    return wrapper


def log_func_exe_time(fn):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = fn(*args, **kwargs)
        end = time.time()
        LOG.debug(_('function %s takes %s seconds.') %
                        (inspect.getmodule(fn), str(end - start)))
        return result
    return wrapper


def get_lower_case_value_by_key(item, key):
    value = get_value_by_key(item, key)
    if value and (type(value) is str or type(value) is unicode):
        return value.lower()
    return value


def get_value_by_key(item, key):
    '''
    :param item: item should be dict object
    :param key: a certain key or looks like a/#list/b
                to search multiple layers.
    '''
    temp = item
    if isinstance(key, list):
        hierarchy_keys = key
    else:
        hierarchy_keys = key.split('/')
    if hierarchy_keys[0] == '#list' and len(hierarchy_keys) <= 1:
        LOG.error(_("hierarchy_keys ends with #list. %s") % temp)
    elif hierarchy_keys[0] == '#list' and len(hierarchy_keys) > 1:
        value_list = []
        for attr in temp:
            value = get_value_by_key(attr, hierarchy_keys[1])
            if value is not None and not isinstance(value, dict) \
                    and not isinstance(value, list):
                value_list.append(value)
            elif value is None:
                # search other attributes
                continue
            else:
                # not support key more than 3 hierarchies.
                LOG.warn(_('Not support searching for item %s and key %s') %
                            (item, key))
        return value_list if len(value_list) > 0 else None
    elif len(hierarchy_keys) == 1:
        return item.get(hierarchy_keys[0], None)
    else:
        key = hierarchy_keys.pop(0)
        return get_value_by_key(item.get(key, {}), hierarchy_keys)


def convert_IP_to_tuple(ip):
    if not ip:
        ip = tuple('')
    if not isinstance(ip, str) and not isinstance(ip, unicode):
        ip = tuple('')
    else:
        ip = tuple(int(part) for part in ip.split('.'))
    return ip


def chunkreadable(iter, chunk_size=65536):
    """
    Wrap a readable iterator with a reader yielding chunks of
    a preferred size, otherwise leave iterator unchanged.

    :param iter: an iter which may also be readable
    :param chunk_size: maximum size of chunk
    """
    return chunkiter(iter, chunk_size) if hasattr(iter, 'read') else iter


def chunkiter(fp, chunk_size=65536):
    """
    Return an iterator to a file-like obj which yields fixed size chunks

    :param fp: a file-like object
    :param chunk_size: maximum size of chunk
    """
    while True:
        chunk = fp.read(chunk_size)
        if chunk:
            yield chunk
        else:
            break


def cooperative_iter(iter):
    """
    Return an iterator which schedules after each
    iteration. This can prevent eventlet thread starvation.

    :param iter: an iterator to wrap
    """
    try:
        for chunk in iter:
            sleep(0)
            yield chunk
    except Exception, err:
        msg = _("Error: cooperative_iter exception %s") % err
        LOG.error(msg)
        raise


def cooperative_read(fd):
    """
    Wrap a file descriptor's read with a partial function which schedules
    after each read. This can prevent eventlet thread starvation.

    :param fd: a file descriptor to wrap
    """
    def readfn(*args):
        result = fd.read(*args)
        sleep(0)
        return result
    return readfn


class CooperativeReader(object):
    """
    An eventlet thread friendly class for reading in image data.

    When accessing data either through the iterator or the read method
    we perform a sleep to allow a co-operative yield. When there is more than
    one image being uploaded/downloaded this prevents eventlet thread
    starvation, ie allows all threads to be scheduled periodically rather than
    having the same thread be continuously active.
    """
    def __init__(self, fd):
        """
        :param fd: Underlying image file object
        """
        self.fd = fd
        if hasattr(fd, 'read'):
            self.read = cooperative_read(fd)

    def __iter__(self):
        return cooperative_iter(self.fd.__iter__())


def image_meta_to_http_headers(image_meta):
    """
    Returns a set of image metadata into a dict
    of HTTP headers that can be fed to either a Webob
    Request object or an httplib.HTTP(S)Connection object

    :param image_meta: Mapping of image metadata
    """
    headers = {}
    for k, v in image_meta.items():
        if v is not None:
            if k == 'properties':
                for pk, pv in v.items():
                    if pv is not None:
                        headers["x-image-meta-property-%s"
                                % pk.lower()] = unicode(pv)
            else:
                headers["x-image-meta-%s" % k.lower()] = unicode(v)
    return headers


def add_features_to_http_headers(features, headers):
    """
    Adds additional headers representing glance features to be enabled.

    :param headers: Base set of headers
    :param features: Map of enabled features
    """
    if features:
        for k, v in features.items():
            if v is not None:
                headers[k.lower()] = unicode(v)


def get_image_meta_from_headers(response):
    """
    Processes HTTP headers from a supplied response that
    match the x-image-meta and x-image-meta-property and
    returns a mapping of image metadata and properties

    :param response: Response to process
    """
    result = {}
    properties = {}

    if hasattr(response, 'getheaders'):  # httplib.HTTPResponse
        headers = response.getheaders()
    else:  # webob.Response
        headers = response.headers.items()

    for key, value in headers:
        key = str(key.lower())
        if key.startswith('x-image-meta-property-'):
            field_name = key[len('x-image-meta-property-'):].replace('-', '_')
            properties[field_name] = value or None
        elif key.startswith('x-image-meta-'):
            field_name = key[len('x-image-meta-'):].replace('-', '_')
            result[field_name] = value or None
    result['properties'] = properties
    if 'size' in result:
        try:
            result['size'] = int(result['size'])
        except ValueError:
            raise exception.Invalid
    for key in ('is_public', 'deleted', 'protected'):
        if key in result:
            result[key] = bool_from_string(result[key])
    return result


def bool_from_string(subject):
    """Interpret a string as a boolean-like value."""
    if isinstance(subject, bool):
        return subject
    elif isinstance(subject, int):
        return subject == 1
    if hasattr(subject, 'startswith'):  # str or unicode...
        if subject.strip().lower() in ('true', 'on', '1', 'yes', 'y'):
            return True
    return False


def generate_uuid():
    return str(uuid.uuid4())


def is_uuid_like(value):
    try:
        uuid.UUID(value)
        return True
    except Exception:
        return False


def safe_mkdirs(path):
    try:
        os.makedirs(path)
    except OSError, e:
        if e.errno != errno.EEXIST:
            raise


def safe_remove(path):
    try:
        os.remove(path)
    except OSError, e:
        if e.errno != errno.ENOENT:
            raise


class LoopingCallDone(Exception):
    """Exception to break out and stop a LoopingCall.

    The poll-function passed to LoopingCall can raise this exception to
    break out of the loop normally. This is somewhat analogous to
    StopIteration.

    An optional return-value can be included as the argument to the exception;
    this return-value will be returned by LoopingCall.wait()

    """

    def __init__(self, retvalue=True):
        """:param retvalue: Value that LoopingCall.wait() should return."""
        self.retvalue = retvalue


class LoopingCall(object):
    def __init__(self, f=None, *args, **kw):
        self.args = args
        self.kw = kw
        self.f = f
        self._running = False

    def start(self, interval, initial_delay=None):
        self._running = True
        done = event.Event()

        def _inner():
            if initial_delay:
                greenthread.sleep(initial_delay)

            try:
                while self._running:
                    self.f(*self.args, **self.kw)
                    if not self._running:
                        break
                    greenthread.sleep(interval)
            except LoopingCallDone, e:
                self.stop()
                done.send(e.retvalue)
            except Exception:
                LOG.exception(_('in looping call'))
                done.send_exception(*sys.exc_info())
                return
            else:
                done.send(True)

        self.done = done

        greenthread.spawn(_inner)
        return self.done

    def stop(self):
        self._running = False

    def wait(self):
        return self.done.wait()


class PrettyTable(object):
    """Creates an ASCII art table for use in bin/glance

    Example:

        ID  Name              Size         Hits
        --- ----------------- ------------ -----
        122 image                       22     0
    """
    def __init__(self):
        self.columns = []

    def add_column(self, width, label="", just='l'):
        """Add a column to the table

        :param width: number of characters wide the column should be
        :param label: column heading
        :param just: justification for the column, 'l' for left,
                     'r' for right
        """
        self.columns.append((width, label, just))

    def make_header(self):
        label_parts = []
        break_parts = []
        for width, label, _ in self.columns:
            # NOTE(sirp): headers are always left justified
            label_part = self._clip_and_justify(label, width, 'l')
            label_parts.append(label_part)

            break_part = '-' * width
            break_parts.append(break_part)

        label_line = ' '.join(label_parts)
        break_line = ' '.join(break_parts)
        return '\n'.join([label_line, break_line])

    def make_row(self, *args):
        row = args
        row_parts = []
        for data, (width, _, just) in zip(row, self.columns):
            row_part = self._clip_and_justify(data, width, just)
            row_parts.append(row_part)

        row_line = ' '.join(row_parts)
        return row_line

    @staticmethod
    def _clip_and_justify(data, width, just):
        # clip field to column width
        clipped_data = str(data)[:width]

        if just == 'r':
            # right justify
            justified = clipped_data.rjust(width)
        else:
            # left justify
            justified = clipped_data.ljust(width)

        return justified


def get_terminal_size():

    def _get_terminal_size_posix():
        import fcntl
        import struct
        import termios

        height_width = None

        try:
            height_width = struct.unpack('hh', fcntl.ioctl(sys.stderr.fileno(),
                                        termios.TIOCGWINSZ,
                                        struct.pack('HH', 0, 0)))
        except:
            pass

        if not height_width:
            try:
                p = subprocess.Popen(['stty', 'size'],
                                    shell=False,
                                    stdout=subprocess.PIPE,
                                    stderr=open(os.devnull, 'w'))
                result = p.communicate()
                if p.returncode == 0:
                    return tuple(int(x) for x in result[0].split())
            except:
                pass

        return height_width

    def _get_terminal_size_win32():
        try:
            from ctypes import windll, create_string_buffer
            handle = windll.kernel32.GetStdHandle(-12)
            csbi = create_string_buffer(22)
            res = windll.kernel32.GetConsoleScreenBufferInfo(handle, csbi)
        except:
            return None
        if res:
            import struct
            unpack_tmp = struct.unpack("hhhhHhhhhhh", csbi.raw)
            (bufx, bufy, curx, cury, wattr,
            left, top, right, bottom, maxx, maxy) = unpack_tmp
            height = bottom - top + 1
            width = right - left + 1
            return (height, width)
        else:
            return None

    def _get_terminal_size_unknownOS():
        raise NotImplementedError

    func = {'posix': _get_terminal_size_posix,
            'win32': _get_terminal_size_win32}

    height_width = func.get(platform.os.name, _get_terminal_size_unknownOS)()

    if height_width == None:
        raise exception.Invalid()

    for i in height_width:
        if not isinstance(i, int) or i <= 0:
            raise exception.Invalid()

    return height_width[0], height_width[1]


def mutating(func):
    """Decorator to enforce read-only logic"""
    @functools.wraps(func)
    def wrapped(self, req, *args, **kwargs):
        if req.context.read_only:
            msg = _("Read-only access")
            LOG.debug(msg)
            raise exc.HTTPForbidden(msg, request=req,
                                    content_type="text/plain")
        return func(self, req, *args, **kwargs)
    return wrapped
