""" Extensions management and implementation """

import inspect
import time
from abc import ABC, abstractmethod
from enum import StrEnum
from typing import List, Optional

from farms_app.console import console
from farms_app.core.window import BaseWindow, MainExtensionWindow
from farms_core import pylog
from imgui_bundle import imgui
from stevedore import EnabledExtensionManager, extension


EXTENSION_NAMESPACE = "farms.app.extension"


###########
# Manager #
###########
class ExtensionCategory(StrEnum):
    """Categories for organizing and discovering extensions.

    - UI: Extensions that contribute user interface elements or interactive components
      and must always run on the core process.

    - WORKFLOW: Extensions that define or modify execution flow of FARMS, processing
    steps, and can read/write simulation data, add workflow windows. Can run on
    experimental processes.

    - CUSTOM: Extensions that do not fit into a standard category, often experimental or
    new domains that are outside the core of FARMS. Can run on external processes.

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

    def __init__(self, fail_on_load=True):
        super().__init__()
        self.fail_on_load = fail_on_load
        self._enabled_exts: dict[str, EnabledExtension] = {}

        self._mgr = EnabledExtensionManager(
            namespace=EXTENSION_NAMESPACE,
            check_func=self.check_cb,
            on_load_failure_callback=self.load_error_cb,
        )

    def load_error_cb(self, manager, entry_point, exception):
        pylog.error(f"Could not load extension {entry_point} by {manager}")
        if self.fail_on_load:
            console.print_exception()

    def check_cb(self, ext: 'BaseExtension'):
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
            # Move this code to the window manager
            for window in self._enabled_exts[name].obj.windows:
                window.initialize()
            pylog.info(f"Enabled extension {name}")
        except Exception as e:
            pylog.error(f"Failed enabling extension {name} with error: {e}")
            console.print_exception(show_locals=True)
            return False

    def disable(self, name: str) -> bool:
        """ Disable a plugin """

        if name not in self._enabled_exts:
            pylog.error(f"Requested extension {name} is not available")
            return False

        try:
            del self._enabled_exts[name]
        except Exception as e:
            pylog.error(f"Error in unregister() for module {name}: {e}")
            console.print_exception(show_locals=True)
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
            return False

        # First disable the extension
        self.disable(name)
        # Remove the extension from cache
        for index, entry_point in list(self._mgr.ENTRY_POINT_CACHE[EXTENSION_NAMESPACE]):
            if name == entry_point.name:
                break
        self._mgr.ENTRY_POINT_CACHE[EXTENSION_NAMESPACE].pop(index)
        pylog.debug(f"Removing extension {name} from loaded extensions")
        return True

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


##############
# Extensions #
##############
class BaseExtension(ABC):
    """Extension base  class"""

    def __init__(self, name: str):

        self.name = name
        self.hide: bool = False
        self.windows: List[BaseWindow] = []
        self._performance_warnings: List[str] = []
        self.main_window = None

    ###########
    # Windows #
    ###########
    def register_window(self, window: BaseWindow):
        """ Register a new window """
        self.windows.append(window)
        # if self._window_manager:
        #     self._window_manager.register_window(window)

    def create_main_window(self) -> MainExtensionWindow:
        """Create the main extension window with dockspace"""
        if self.main_window is None and self._needs_main_window:
            self.main_window = MainExtensionWindow(self)
            self.register_window(self.main_window)
            return self.main_window
        else:
            return None

    def unregister_window(self, window: BaseWindow):
        """Unregister a window from this extension"""
        if window in self.windows:
            self.windows.remove(window)
        # if self._window_manager:
        #     self._window_manager.unregister_window(window)

    def show_all_windows(self):
        """Show all windows for this extension"""
        for window in self.windows:
            window.show()

    def hide_all_windows(self):
        """Hide all windows for this extension"""
        for window in self.windows:
            window.hide()

    def dock_all_windows_to_extension(self):
        """Dock all windows back to extension dockspace"""
        for window in self.windows:
            if window != self.main_window:
                window._should_dock_to_extension = True

    #############
    # Lifecycle #
    #############
    def before_render(self) -> None:
        """Steps to perform before calling the renderer."""
        return

    def on_render(self) -> None:
        """ Called during every render cycle """

    @abstractmethod
    def render(self) -> None:
        """Main render loop for this extension."""

    def after_render(self) -> None:
        """Steps to perform after calling the renderer."""
        return

    def update(self):
        """ Calls the extension update """
        self.on_update()

    @abstractmethod
    def on_update(self):
        """ On update called before rendering """

    def event(self):
        """ Call the user implemented on_event method """
        self.on_event()

    @abstractmethod
    def on_event(self):
        """ On event """

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources before shutdown or reload."""

    def _needs_main_window(self) -> bool:
        """Override to specify if extension needs a main docking window"""
        return True

    ############
    # Metadata #
    ############
    def get_info(self) -> dict:
        """Return extension metadata (override if needed)."""
        return {
            "name": self.name,
            "windows": self.windows,
            "hidden": self.hide,
        }

    @abstractmethod
    def get_dependencies(self) -> List[str]:
        """Return a list of dependencies that this extension requires."""

    ####################
    # State management #
    ####################
    def on_enable(self) -> bool:
        """Enable the extension (return True on success)."""

    def on_disable(self) -> bool:
        """Disable the extension (return True on success)."""

    def on_reload(self) -> bool:
        """Safely reload and reinitialize the extension."""

    ###########
    # Utility #
    ###########
    def create_window_id(self, window_name: str) -> str:
        """Create a unique window identifier for this extension."""
        return f"{window_name}##{self.name}"

    def _render_with_timing(self) -> None:
        """Render extension with performance timing and warnings."""
        start_time = time.perf_counter()

        try:
            self.render()
        except Exception as e:
            imgui.text_colored((1, 0, 0, 1), f"⚠️ Widget Error: {e}")
            return

        render_time = time.perf_counter() - start_time

        # Warn about slow renders
        if render_time > 0.03:  # ~30 FPS threshold
            warning = f"Slow render: {render_time*1000:.1f} ms"
            self._performance_warnings.append(warning)
            print(f"⚠️ Extension '{self.name}': {warning}")

        self._show_performance_warnings()

    def _show_performance_warnings(self) -> None:
        """Display performance warnings in the GUI."""
        if not self._performance_warnings:
            return

        imgui.separator()
        imgui.text_colored((1, 1, 0, 1), "⚠️ Performance Warnings:")
        for warning in self._performance_warnings[-3:]:  # Show last 3
            imgui.text_colored((1, 1, 0, 1), f"  {warning}")

        if imgui.button("Clear Warnings"):
            self._performance_warnings.clear()


class UIExtension(BaseExtension):
    """
    Full app interface access.
    Can modify menus, toolbars, status bars, and global UI.
    """

    CATEGORY = ExtensionCategory.UI

    def __init__(self, name: str):
        super().__init__(name=name)

    def _needs_main_window(self) -> bool:
        """UI extensions typically don't need their own docking space"""
        return False

    # @abstractmethod
    def before_render(self) -> None:
        """ Steps to perform before calling the renderer """

    def render(self) -> None:
        """ Main render """

        # Call the user render function
        self.on_render()

        for window in self.windows:
            window.on_render()

    # @abstractmethod
    def after_render(self) -> None:
        """ Steps to perform before calling the renderer """

    def on_update(self):
        """ On update called before rendering """

    def on_event(self):
        """ On event """


class WorkflowExtension(BaseExtension):
    """
    FARMS domain access.
    Can read/write simulation data, add workflow windows.
    """

    CATEGORY = ExtensionCategory.WORKFLOW

    def __init__(self, name: str):
        super().__init__(name=name)
        self.register_window(MainExtensionWindow(self))
        self._farms_data = None # Set by plugin manager
        self.stage: Optional[str] = None

    @property
    def farms_data(self):
        """ Get farms data """
        return self._farms_data

    @farms_data.setter
    def farms_data(self, value):
        """ Farms data setter """
        if self._farms_data is not None:
            raise ValueError("Cannot override already initialized simulation data")
        self._farms_data = value

    def render_menu(self):
        """ Render menu """
        pass

    def before_render(self):
        pass

    def render(self):
        if self.hide:
            return

        # Call the user render function
        self.on_render()

        # Render other associated windows
        for window in self.windows:
            if window._should_dock_to_extension:
                # Reset if True
                window._should_dock_to_extension = False
                imgui.set_next_window_dock_id(
                    self.windows[0].dockspace_id,
                    cond=imgui.Cond_.always
                )
            window._render()

    def after_render(self):
        pass

    def on_update(self):
        """ On update called before rendering """

    def on_event(self):
        """ On event """


class CustomExtension(BaseExtension):
    """
    Independent / standalone extensions.
    Minimal host context; no FARMS data required.
    user experiments, visualizations, no communication between extensions
    """

    CATEGORY = ExtensionCategory.CUSTOM

    def __init__(self, name: str):
        # No special data access
        super().__init__(name=name)
        self.register_window(MainExtensionWindow(self))

    def render_menu(self):
        """ Render menu """
        pass

    def before_render(self):
        pass

    def render(self):

        if self.hide:
            return

        # Call the user render function
        self.on_render()

        # Render other associated windows
        for window in self.windows:
            if window._should_dock_to_extension:
                # Reset if True
                window._should_dock_to_extension = False
                imgui.set_next_window_dock_id(
                    self.windows[0].dockspace_id,
                    cond=imgui.Cond_.always
                )
            window._render()

    def on_update(self):
        """ On update called before rendering """

    def on_event(self):
        """ On event """
