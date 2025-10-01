""" Extensions management and implementation """

import inspect
import time
from abc import ABC, abstractmethod
from enum import StrEnum
from typing import List, Optional

from farms_app.core.window import BaseWindow, MainExtensionWindow
from farms_core import pylog
from imgui_bundle import imgui
from rich.console import Console
from stevedore import EnabledExtensionManager, extension

EXTENSION_NAMESPACE = "farms.app.extension"


###########
# Manager #
###########
class ExtensionCategory(StrEnum):
    """Categories for organizing and discovering extensions.

    - UI: Extensions that contribute user interface elements or interactive components.

    - WORKFLOW: Extensions that define or modify execution flow, processing steps, and
    can read/write simulation data, add workflow windows.

    - CUSTOM: Extensions that do not fit into a standard category, often experimental or
    new domains that are outside the core of FARMS.

    """
    UI = "ui"
    WORKFLOW = "workflow"
    CUSTOM = "custom"


class ExtensionManager:
    """Manager class for all App Extensions under the namespace farms.app

    Responsibilities:
    - Plugin discovery from multiple sources
    - Dependency resolution and loading order
    - Runtime enable/disable
    - Hot-reloading for development
    """
    console = Console()

    def __init__(self, fail_on_load=True):
        super().__init__()
        self.fail_on_load = fail_on_load
        self._enabled_exts: dict[str, EnabledExtension] = {}
        self._disabled_exts = []

        self._mgr = EnabledExtensionManager(
            namespace=EXTENSION_NAMESPACE,
            check_func=self.check_cb,
            on_load_failure_callback=self.load_error_cb,
        )

    def load_error_cb(self, manager, entry_point, exception):
        pylog.error(f"Could not load extension {entry_point} by {manager}")
        if self.fail_on_load:
            ExtensionManager.console.print_exception()

    def check_cb(self, ext: extension):
        return (
            inspect.isclass(ext.plugin) and issubclass(ext.plugin, BaseExtension)
        )

    @property
    def names(self):
        return self._mgr.names()

    def enable(self, name: str) -> bool:
        """ Instantiate the loaded extension """

        if name not in self.names:
            pylog.error(f"Requested extension {name} is not available")
            return False

        try:
            _ext = self._mgr[name]
            self._enabled_exts[name] = EnabledExtension(
                entry_point=_ext.entry_point,
                obj=_ext.plugin(),
                category=ExtensionManager._get_type(_ext.plugin)
            )
        except Exception as e:
            pylog.error(f"Failed enabling extension {name} with error: {e}")
            ExtensionManager.console.print_exception(show_locals=True)
            return False

    def disable(self, name: str) -> bool:
        """ Disable a plugin """

        if name not in self._enabled_exts:
            pylog.error(f"Requested extension {name} is not available")
            return False

        try:
            del self._enabled_exts[name]
            self._disabled_exts.pop(self._disabled_exts.index(name))
        except Exception as e:
            pylog.error(f"Error in unregister() for module {name}: {e}")
            ExtensionManager.console.print_exception(show_locals=True)
            return False

    @staticmethod
    def _get_type(ext):
        """Auto-detect plugin type from class hierarchy"""
        if issubclass(ext, UIExtension):
            return ExtensionCategory.UI
        elif issubclass(ext, WorkflowExtension):
            return ExtensionCategory.WORKFLOW
        elif issubclass(ext, CustomExtension):
            return ExtensionCategory.CUSTOM
        else:
            raise TypeError(f"Unknown extension type for class {ext}")

    def unload(self, name: str) -> bool:
        if name not in self._mgr:
            pylog.error(f"Unknown extension {name} cannot be unloaded")
            return
        else:
            # First disable the extension
            self.disable_extension(name)
            # Remove the extension from cache
            for index, entry_point in list(self._mgr.ENTRY_POINT_CACHE[EXTENSION_NAMESPACE]):
                if name == entry_point.name:
                    break
            self._mgr.ENTRY_POINT_CACHE[EXTENSION_NAMESPACE].pop(index)
            pylog.debug(f"Removing extension {name} from loaded extensions")

    def render_all(self):
        """Render all enabled extensions and their windows"""
        # Render extension logic
        for enabled_ext in self._enabled_exts.values():
            try:
                enabled_ext.obj.before_render()
                enabled_ext.obj.render()
                enabled_ext.obj.after_render()
            except Exception as e:
                print(f"Error rendering extension {enabled_ext.obj.name}: {e}")


class EnabledExtension:
    """ Manager for enabled extension """

    def __init__(self, entry_point: str, obj: 'BaseExtension', category: ExtensionCategory):
        super().__init__()
        self.entry_point: str = entry_point
        self.obj: BaseExtension = obj
        self.enabled = False
        self.category: ExtensionCategory = category


