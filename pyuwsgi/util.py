import os
import fcntl
import errno
import random
from multiprocessing.sharedctypes import Value as SharedValue

from .errors import ApplicationError


class shared_property(object):

    def __init__(self, name, type, initial=None, readonly=True, lock=False):
        self.name = '_' + name
        self.type = type
        self.readonly = readonly
        self.initial = initial
        self.lock = lock

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        if self.name not in instance.__dict__:
            setattr(instance, self.name, SharedValue(self.type, lock=self.lock))
            instance.__dict__[self.name].value = self.initial
        return instance.__dict__[self.name].value

    def __set__(self, instance, value):
        if self.readonly:
            raise AttributeError('Attribute is read-only')
        if self.name not in instance.__dict__:
            setattr(instance, self.name, SharedValue(self.type, lock=self.lock))
        instance.__dict__[self.name].value = value


def kill(pid, sig):
    try:
        os.kill(pid, sig)
    except OSError as e:
        if e.errno not in [errno.ESRCH]:
            raise


def close(fd):
    if hasattr(fd, 'close'):
        fd.close()
    else:
        os.close(fd)


def set_process_title(title):
    pass


def seed():
    random.seed(os.urandom(128))


def set_blocking(fd):
    if hasattr(fd, 'setblocking'):
        fd.setblocking(1)
    else:
        if hasattr(fd, 'fileno'):
            fd = fd.fileno()
        flags = fcntl.fcntl(fd, fcntl.F_GETFD) & ~os.O_NONBLOCK
        fcntl.fcntl(fd, fcntl.F_SETFL, flags)


def set_not_blocking(fd):
    if hasattr(fd, 'setblocking'):
        fd.setblocking(0)
    else:
        if hasattr(fd, 'fileno'):
            fd = fd.fileno()
        flags = fcntl.fcntl(fd, fcntl.F_GETFD) | os.O_NONBLOCK
        fcntl.fcntl(fd, fcntl.F_SETFL, flags)


def set_close_on_exec(fd):
    if hasattr(fd, 'fileno'):
        fd = fd.fileno()
    flags = fcntl.fcntl(fd, fcntl.F_GETFD) | fcntl.FD_CLOEXEC
    fcntl.fcntl(fd, fcntl.F_SETFL, flags)


def import_name(import_string):
    parts = import_string.split(':', 1)
    module_name = parts[0]
    app_name = parts[1] if len(parts) > 1 else 'application'
    try:
        module = __import__(module_name)
        app = getattr(module, app_name)
        if not callable(app):
            raise ApplicationError('WSGI-application must be callable object.')
    except ImportError:
        raise ApplicationError('Cannot import module: {}.'.format(module_name))
    except AttributeError:
        raise ApplicationError('Cannot find object: {}.'.format(app_name))
    return app


def daemonize(umask=0):
    if os.fork():
        os._exit(0)

    os.setsid()

    os.umask(umask)

    with os.open(os.devnull, os.O_RDWR) as null:
        os.dup2(null, 0)
        os.dup2(null, 1)
        os.dup2(null, 2)
