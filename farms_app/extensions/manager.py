""" Plugin Manager """

import inspect
import traceback
from abc import ABC
from enum import StrEnum
from typing import Type
from rich.console import Console

from farms_core import pylog
from stevedore import DriverManager, EnabledExtensionManager, extension

from .base import (BaseExtension, CustomExtension, UIExtension,
                   WorkflowExtension)


class InterfaceCategory(StrEnum):
    UI = "ui"
    WORKFLOW = "workflow"
    CUSTOM = "custom"


class EnabledExtension:
    """ Manager for enabled extension """

    def __init__(self, entry_point: str, obj: BaseExtension, category: InterfaceCategory):
        super().__init__()
        self.namespace: str = "farms.app.interface"
        self.entry_point: str = entry_point
        self.obj: BaseExtension = obj
        self.active = False
        self.category: InterfaceCategory = category


def create_ext_load_error_cb(fail_on_load=True):
    def ext_load_error_cb(manager, entry_point, exception):
        pylog.error(f"Could not load extension {entry_point} by {manager}")
        AppExtensionManager.console.print_exception(exception)
        if fail_on_load:
            raise exception
    return ext_load_error_cb


def create_ext_check_func(base_extension: ABC):
    def ext_check_func(ext):
        if (inspect.isclass(ext.plugin) and issubclass(ext.plugin, base_extension)):
            return True
        else:
            return False
    return ext_check_func


class BaseExtensionManager(ABC):
    """ Base class defining extension managers in FARMS

    Responsibilities:
    - Namespace based plugin discovery from multiple sources
    - Dependency resolution and loading order
    - Enable/Disable flags
    - Hot-reloading for development

    """

    def __init__(
            self,
            namespace: str,
            manager_type: Type = extension.ExtensionManager,
            **manager_kwargs
    ):
        super().__init__()

        self.namespace: str = namespace
        self.manager_type = manager_type
        self.manager_kwargs = manager_kwargs
        self._discovered_extensions = {}
        self._instantiated_extensions = {}

    def discover(self):
        """ Discover """
        self._manager = self.manager_type(
            namespace=self.namespace,
            invoke_on_load=self.invoke_on_load,
            **manager_kwargs
        )

    def instantiate(self, name: str, *args, **kwargs):
        """ instatiate """
        pass

    def get_instance(self, name: str):
        """ Get instance of an instatiated extension """
        pass


class AppExtensionManager():
    """Manager class for all App Extensions under the namespace farms.app

    Responsibilities:
    - Plugin discovery from multiple sources
    - Dependency resolution and loading order
    - Runtime enable/disable
    - Hot-reloading for development
    """
    console = Console()

    def __init__(self, namespace: str):
        super().__init__()

        interface_ext_check_func = create_ext_check_func(BaseExtension)
        interface_load_error_cb = create_ext_load_error_cb(fail_on_load=True)

        self.interface_mgr = EnabledExtensionManager(
            namespace=namespace,
            check_func=interface_ext_check_func,
            on_load_failure_callback=interface_load_error_cb,
        )

        # self.renderer_mgr = DriverManager(
        #     namespace='farms.app.backend',
        #     name="opengl2",
        # )

        # self.platform,_mgr = DriverManager(
        #     namespace='farms.app.platform',
        #     name="glfw",
        # )

        #
        self._enabled_exts: dict[str, EnabledExtension] = {}
        self._disabled_exts = []

    @property
    def names(self):
        return self.interface_mgr.names()

    def enable_extension(self, name: str) -> bool:
        """ Instantiate the loaded extension """

        if name not in self.names:
            pylog.error(f"Requested extension {name} is not available")
            return False

        try:
            _ext = self.interface_mgr[name]
            self._enabled_exts[name] = EnabledExtension(
                entry_point=_ext.entry_point,
                obj=_ext.plugin(),
                category=AppExtensionManager._get_extension_type(_ext.plugin)
            )
        except Exception as e:
            pylog.error(f"Failed enabling extension {name} with error: {e}")
            AppExtensionManager.console.print_exception(show_locals=True)
            return False

    def disable_extension(self, name: str) -> bool:
        """ Disable a plugin """

        if name not in self._enabled_exts:
            pylog.error(f"Requested extension {name} is not available")
            return False

        try:
            del self._enabled_exts[name]
            self._disabled_exts.pop(self._disabled_exts.index(name))
        except Exception as e:
                pylog.error(f"Error in unregister() for module {name}: {e}")
                return False

    @staticmethod
    def _get_extension_type(ext):
        """Auto-detect plugin type from class hierarchy"""
        if issubclass(ext, UIExtension):
            return InterfaceCategory.UI
        elif issubclass(ext, WorkflowExtension):
            return InterfaceCategory.WORKFLOW
        elif issubclass(ext, CustomExtension):
            return InterfaceCategory.CUSTOM
        else:
            raise TypeError(f"Unknown plugin type for class {ext}")

    # def unload_plugin(self, name: str) -> bool:
    #     if name not in self.interface_mgr:
    #         pylog.error(f"Unknown plugin {name} cannot be unloaded")
    #         return
    #     else:
    #         try:
    #             for key in list(self.loaded_plugins.keys()): # Iterate over a copy of the key
    #                 if key == plugin_id:
    #                     del self.loaded_plugins[plugin_id]
    #             pylog.debug(f"Removing plugin {plugin_id} from loaded plugins")
    #         except Exception as e:
    #             pylog.error(f"Error in register() for module {plugin_id}: {e}")
    #             return False
