# -*- coding: utf-8 -*-
"""
Simple plugin-like system for tasks and hardware

Adapted from
http://eli.thegreenplace.net/2012/08/07/fundamental-concepts-of-plugin-infrastructures
https://github.com/cortex-lab/phy/blob/master/phy/utils/plugin.py
"""
import pdb
import os
from abc import ABCMeta
import os.path as op
# import imp
import importlib
from pathlib import Path
import json
import inspect
import sys
import typing

from autopilot import prefs
from autopilot.core.loggers import init_logger


def _fullname(o):
    """Return the fully-qualified name of a function."""
    return o.__module__ + "." + o.__name__ if o.__module__ else o.__name__


class Registry(type):
    """
    Factory metaclass to make registries.

    Each registry keeps track of `_items` in a dictionary. `_items` is initially None,
    and is created as each sub_registry is used for the first time. Otherwise, subregistries
    inherit the top-level _items dictionary and they all have the same elements.

    The Registry then keeps track of objects that it creates using the __init__ method.
    """
    _items = None # type: dict
    _instances = None # type: typing.Dict[str, typing.Dict[str, typing.Any]]
    """
    Register all instances of objects created.
    
    Store in a dict like ``{'class_name': {'instance_id':instance}}``
    
    Make sure objects have unique IDs, either given as their ``id`` attribute, typically taken from their id
    specified in prefs
    """
    _logger = None
    _plugin_classes = None
    """
    list of classes that are imported through plugins.
    """

    _plugin_modules = [] # type: list
    """
    Keep a list of plugin modules imported with :meth:`.import_plugins` common to all registries so they can
    check if the object is in one of those registries.
    """

    def __init__(cls, name, bases, attrs):
        """
        Add the newly created item to the _items dictionary and register it!!
        """
        # print('init')
        # pdb.set_trace()

        cls._items[name] = cls
        type.__init__(cls, name, bases, attrs)

    def __new__(cls, name, bases, attrs):
        """
        Called with the Sub-Registry as the cls attribute,
        create the _items dictionary if none has been created yet.
        """
        # print('new')
        # pdb.set_trace()

        if cls._items is None:
            cls._items = {}
            cls._instances = {}
            cls._plugin_classes = []
            cls._logger = init_logger(module_name='registry', class_name=cls.__name__)
            cls.init_registry()

        return type.__new__(cls, name, bases, attrs)
    #
    # @classmethod
    # def register(cls, **kwargs):
    #     """
    #     If subclassing don't work for some reason, a decorator ya can use to register
    #
    #     .. Examples::
    #
    #         @HardwareRegistry.register
    #         class Some_Hardware_Object(Hardware):
    #             pass
    #
    #     """
    #
    #     def decorator(cls_):
    #         pdb.set_trace()
    #         cls._items[cls_.__name__] = cls_
    #         # if _fullname(cls_) not in (_fullname(_) for _ in HardwareRegistry.devices):
    #         #     # print("Register hardware", _fullname(cls_))  # TODO: use logger
    #         #     cls.devices.append(cls_)
    #         return cls_
    #     return decorator

    @classmethod
    def get_names(cls):
        return list(cls._items.keys())

    @classmethod
    def get(cls, key):
        return cls._items[key]

    @classmethod
    def register_instance(cls, new_instance):
        cls._instances[new_instance.__class__.__name__] = new_instance

    @classmethod
    def init_registry(cls):
        """
        Hook to call once when the registry is first invoked.
        """
        pass

    @classmethod
    def import_plugins(cls):
        """
        Iterate through python files in ``prefs.PLUGINDIR``, importing them, and thus registering them!

        """

        plugin_dir = prefs.get('PLUGINDIR')
        if plugin_dir is None:
            cls._logger.warning('No plugin dir found!')
            return

        # recursively list python files in plugin directory
        plugin_files = Path(plugin_dir).glob('**/*.py')
        for pfile in plugin_files:
            # prepend autopilot.plugins to avoid namespace clashes and make them uniformly moduled
            module_name = 'autopilot.plugins.' + inspect.getmodulename(pfile)

            # import module
            try:
                if module_name in sys.modules:
                    mod = sys.modules[module_name]
                else:
                    mod_spec = importlib.util.spec_from_file_location(module_name, pfile)
                    mod = importlib.util.module_from_spec(mod_spec)
                    mod_spec.loader.exec_module(mod)
                    sys.modules[module_name] = mod
            except Exception as e:
                cls._logger.exception(f'plugin file {str(pfile)} could not be imported, got exception: {e}')
                continue

            # get the imported modules and check if they're one of ours
            # filter for classes, and then filter if the class of the class (aka the metaclass, aka the registry)
            # if this particular registry
            members = [m for m in inspect.getmembers(mod) if inspect.isclass(m[1]) and m[1].__class__ is cls]
            if len(members)>0:
                for m in members:
                    if m not in cls._plugin_classes:
                        cls._plugin_classes.append(m)







class TaskRegistry(Registry):

    @classmethod
    def init_registry(cls):
        cls.import_plugins()
        import autopilot.tasks







class HardwareRegistry(Registry):
    """Register hardware instances using decorators

    Basic usage:

    @HardwareRegistry.register()
    class MyHardwareClass(Hardware):
        ...

    """

    devices = []



    @classmethod
    def init_registry(cls):
        cls.import_plugins()
        import autopilot.hardware

    @classmethod
    def list_hardware(cls):
        hw_category = {}
        for class_name, class_object in cls._items.items():
            cg =  class_object.category
            if cg == class_name or class_name == "Hardware":
                # don't return metaclasses
                continue
            if cg is None:
                cg = 'Uncategorized'
            elif cg not in hw_category:
                hw_category[cg] = []
            hw_category[cg].append(class_name)

        return hw_category


def load_user_paths():
    """Read user paths from BASEDIR/user_paths.json (or create file if it does not exit)"""

    from autopilot.tasks.task import Task

    path_file = Path(prefs.get('BASEDIR')) / 'user_paths.json'

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
