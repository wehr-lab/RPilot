# -*- coding: utf-8 -*-
"""
Simple plugin-like system for tasks and hardware

Adapted from
http://eli.thegreenplace.net/2012/08/07/fundamental-concepts-of-plugin-infrastructures
https://github.com/cortex-lab/phy/blob/master/phy/utils/plugin.py
"""

import os
import os.path as op
import imp
import importlib
from pathlib import Path
import json

from autopilot import prefs


def _fullname(o):
    """Return the fully-qualified name of a function."""
    return o.__module__ + "." + o.__name__ if o.__module__ else o.__name__


class TaskRegistry(type):
    """Register all task instances."""

    tasks = []

    def __init__(cls, name, bases, attrs):
        if name != 'Task':
            if _fullname(cls) not in (_fullname(_) for _ in TaskRegistry.tasks):
                # print("Register task", _fullname(cls))  # TODO: use logger
                TaskRegistry.tasks.append(cls)

    @classmethod
    def get_task_names(cls):
        return [x.get_name() for x in TaskRegistry.tasks]

    @classmethod
    def get_class_from_name(mcs, name):
        """This will return None for unregistered classes"""

        cls = None

        names = TaskRegistry.get_task_names()
        if name in names:
            cls = TaskRegistry.tasks[names.index(name)]

        return cls


class HardwareRegistry(type):
    """Register hardware instances using decorators

    Basic usage:

    @HardwareRegistry.register()
    class MyHardwareClass(Hardware):
        ...

    """

    devices = []

    @classmethod
    def register(cls, **kwargs):
        def decorator(cls_):
            if _fullname(cls_) not in (_fullname(_) for _ in HardwareRegistry.devices):
                # print("Register hardware", _fullname(cls_))  # TODO: use logger
                cls.devices.append(cls_)
            return cls_
        return decorator


def load_user_paths():
    """Read user paths from BASEDIR/user_paths.json (or create file if it does not exit)"""

    from autopilot.tasks.task import Task

    path_file = Path(prefs.BASEDIR) / 'user_paths.json'

    if not path_file.exists():

        with path_file.open('w') as f:
            json.dump({'USER_PATHS': [],
                       'USER_CLASSES': []}, f,
                      indent=4)

    try:
        with path_file.open('r') as f:
            user_data = json.load(f)
    except:
        user_data = {'USER_PATHS': [],
                     'USER_CLASSES': []}

    return user_data


def initialize_registries():
    """Register built-in and user-defined tasks and hardware"""

    # First register built-in tasks and hardware
    import autopilot.tasks
    import autopilot.hardware

    # Try to find classes in user paths
    user_data = load_user_paths()
    discover_plugins(user_data['USER_PATHS'])

    # Import user classes
    for cls in user_data['USER_CLASSES']:
        importlib.import_module(cls)


def _iter_plugin_files(dirs):
    """Iterate through all files."""

    for plugin_dir in dirs:
        plugin_dir = Path(plugin_dir).expanduser()
        if plugin_dir.exists():
            for subdir, dirs, files in os.walk(plugin_dir, followlinks=True):
                subdir = Path(subdir)

                # Skip test folders.
                base = subdir.name
                if 'test' in base or '__' in base or '.git' in str(subdir):  # pragma: no cover
                    continue

                print("Scanning %s" % subdir)
                for filename in files:
                    if (filename.startswith('__') or not filename.endswith('.py')):
                        continue  # pragma: no cover
                    print("Found plugin module `%s`.", filename)
                    yield subdir / filename


def discover_plugins(dirs):
    """Discover the task/hardware classes contained in Python files."""

    # Scan all subdirectories recursively.
    for path in _iter_plugin_files(dirs):

        subdir = path.parent
        modname = path.stem
        if modname == 'autopilot':
            continue

        # TODO: replace imp by importlib
        file, path, descr = imp.find_module(modname, [subdir])
        if file:
            # Loading the module registers the plugin
            try:
                mod = imp.load_module(modname, file, path, descr)  # noqa
            except Exception as e:  # pragma: no cover
                logger.exception(e)
            finally:
                file.close()
