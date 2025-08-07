""" Plugin Manager """

import importlib
import inspect
import os
from pathlib import Path
from typing import Dict, List, Union

from farms_core import pylog

from ..utils.paths import get_project_root
from .base import AppWidget, BaseWidget, CustomWidget, FarmsWidget


FARMS_PLUGIN_ENV = "FARMS_PLUGIN_PATH"


class PluginManager():
    """Manager class for all plugins

    Responsibilities:
    - Plugin discovery from multiple sources
    - Dependency resolution and loading order
    - Runtime enable/disable
    - Hot-reloading for development
    """

    def __init__(self):
        super().__init__()

        # Plugin paths
        self.plugin_paths = [
            get_project_root().joinpath("farms_app", "plugins", "app"),
            get_project_root().joinpath("farms_app", "plugins", "farms"),
            get_project_root().joinpath("farms_app", "plugins", "custom"),
        ]
        # Check for env variables
        if farms_plugin_path := os.getenv("FARMS_PLUGIN_PATH"):
            if not Path(farms_plugin_path).is_dir:
                pylog.warning(f"Plugin path: {farms_plugin_path} is invalid for plugin discovery")
            else:
                self.plugin_paths.append(*PluginManager.get_plugin_paths_from_env())

        # Module tracking for registration and unregister
        self.loaded_plugins = {}  # plugin_id -> module

        # Active modules
        self.active_plugins = {}

        # Widget instances
        self.app_widgets = {}
        self.farms_widgets = {}
        self.custom_widgets = {}

        # Discover plugins
        self.discover_plugins()

    # Plugin Discovery
    def discover_plugins(self) -> None:
        """ Discover plugins """

        for plugin_dir in self.plugin_paths:
            if not plugin_dir.exists():
                continue

            for plugin_file in plugin_dir.glob("*.py"):
                if plugin_file.name.startswith("_"):
                    continue
                try:
                    success = self.load_plugin(plugin_file)
                    if success:
                        pylog.info(f"Loaded plugin: {plugin_file.stem}")
                except Exception as e:
                    pylog.error(f"Failed to load plugin {plugin_file}: {e}")

    def load_plugin(self, plugin_file: Path) -> bool:
        """Load plugin modules """
        # Dynamic import
        spec = importlib.util.spec_from_file_location(plugin_file.stem, plugin_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Validate required components
        if not hasattr(module, 'farms_info'):
            pylog.warning(f"Plugin {plugin_file} missing farms_info")
            return False

        if not hasattr(module, 'register'):
            pylog.warning(f"Plugin {plugin_file} missing register() function")
            return False

        # Validate farms_info
        if not self._validate_plugin_info(module.farms_info):
            return False

        # Store module for unregister
        plugin_id = plugin_file.stem
        self.loaded_plugins[plugin_id] = {
            'file': plugin_file,
            'module': module,
            'info': module.farms_info,
            'active': False,
        }
        return True

    def unload_plugin(self, plugin_id: str) -> bool:
        if plugin_id not in self.loaded_plugins:
            pylog.error(f"Unknown plugin {plugin_id} cannot be unloaded")
            return
        else:
            try:
                module = self.loaded_plugins[plugin_id]['module']
                module.unregister(self)  # This has side effects, returns None
                pylog.debug(f"Removing plugin {plugin_id} from loaded plugins")
                del self.loaded_modules[plugin_id]
            except Exception as e:
                pylog.error(f"Error in register() for module {plugin_id}: {e}")
                del self.loaded_plugins[plugin_id]
                return False

    def enable_plugin(self, plugin_id: str) -> bool:
        """ Register a loaded plugin """
        if plugin_id not in self.loaded_plugins:
            pylog.error(f"Requested plugin {plugin_id} is not available")
            return False
        module = self.loaded_plugins[plugin_id]['module']
        try:
            module.register(self)  # This has side effects, returns None
            pylog.debug(f"Executed register() for module: {module.farms_info['name']}")
            self.loaded_plugins[plugin_id]['active'] = True
            return True  # Success because no error during registration
        except Exception as e:
            pylog.error(f"Error in register() for module {plugin_id}: {e}")
            del self.loaded_plugins[plugin_id]
            return False

    def disable_plugin(self, plugin_id: str) -> bool:
        """ Register a loaded plugin """
        if plugin_id not in self.loaded_plugins:
            pylog.error(f"Requested plugin {plugin_id} is not available")
            return False
        module = self.loaded_plugins[plugin_id]['module']
        try:
            module.unregister(self)  # This has side effects, returns None
            pylog.debug(f"Executed unregister() for module: {module.farms_info['name']}")
            self.loaded_plugins[plugin_id]['active'] = False
            return True  # Success because no error during registration
        except Exception as e:
            pylog.error(f"Error in unregister() for module {plugin_id}: {e}")
            del self.loaded_plugins[plugin_id]
            return False

    def _generate_widget_id_from_class(self, widget_class):
        """Generate widget ID from class name"""
        base_id = widget_class.__name__.lower().replace('widget', '')
        return base_id

    # Register plugins
    def register_class(self, widget_class, **kwargs):
        """Register a widget class directly"""
        # Validate class
        if not (inspect.isclass(widget_class) and issubclass(widget_class, BaseWidget)):
            raise TypeError(f"Expected BaseWidget subclass, got {widget_class}")

        # Auto-detect type
        widget_type = self._detect_widget_type(widget_class)

        # Create instance
        widget_instance = widget_class()

        # Generate ID and register
        widget_id = self._generate_widget_id_from_class(widget_class)
        self._register_widget_by_type(widget_id, widget_instance, widget_type)

    def unregister_class(self, widget_class, **kwargs):
        """UnRegister a widget class directly"""
        # Validate class
        if not (inspect.isclass(widget_class) and issubclass(widget_class, BaseWidget)):
            raise TypeError(f"Expected BaseWidget subclass, got {widget_class}")

        # Auto-detect type
        widget_type = self._detect_widget_type(widget_class)

        # Generate ID and register
        widget_id = self._generate_widget_id_from_class(widget_class)
        self._unregister_widget_by_type(widget_id, widget_type)

    def _register_widget_by_type(self, widget_id: str, widget_instance, widget_type: str):
        """Register widget based on its actual type"""
        try:
            if widget_type == "app":
                self.register_app_widget(widget_id, widget_instance)

            elif widget_type == "farms":
                self.register_farms_widget(widget_id, widget_instance)

            elif widget_type == "custom":
                self.register_custom_widget(widget_id, widget_instance)

        except Exception as e:
            pylog.error(f"Failed to register {widget_type} widget {widget_id}: {e}")

    def _unregister_widget_by_type(self, widget_id: str, widget_type: str):
        """UnRegister widget based on its actual type"""
        try:
            if widget_type == "app":
                self.unregister_app_widget(widget_id)

            elif widget_type == "farms":
                self.unregister_farms_widget(widget_id)

            elif widget_type == "custom":
                self.unregister_custom_widget(widget_id)

        except Exception as e:
            pylog.error(f"Failed to register {widget_type} widget {widget_id}: {e}")

    def _detect_widget_type(self, widget_class):
        """Auto-detect plugin type from class hierarchy"""
        if issubclass(widget_class, AppWidget):
            return "app"
        elif issubclass(widget_class, FarmsWidget):
            return "farms"
        elif issubclass(widget_class, CustomWidget):
            return "custom"
        else:
            raise TypeError(f"Unknown plugin type for class {widget_class}")

    def register_app_widget(self, widget_id: str, widget: AppWidget):
        """ Register App Plugin """
        if widget_id in self.app_widgets:
            pylog.error(f"App Widget with ID {widget_id} already exists in")
            raise KeyError
        self.app_widgets[widget_id] = widget

    def unregister_app_widget(self, widget_id: str):
        """ Register App Widget """
        if widget_id not in self.app_widgets:
            pylog.error(f"App Widget with ID {widget_id} already exists in")
            raise KeyError
        del self.app_widgets[widget_id]

    def register_farms_widget(self, widget_id: str, widget: FarmsWidget):
        """ Register Farms Widget """
        if widget_id in self.farms_widgets:
            pylog.error(f"Farms Widget with ID {widget_id} already exists in")
            raise KeyError
        self.farms_widgets[widget_id] = widget

    def unregister_farms_widget(self, widget_id: str):
        """ Register Farms Widget """
        if widget_id not in self.farms_widgets:
            pylog.error(f"Farms Widget with ID {widget_id} already exists in")
            raise KeyError
        del self.farms_widgets[widget_id]

    def register_custom_widget(self, widget_id: str, widget: CustomWidget):
        """ Register Custom Widget """
        if widget_id in self.custom_widgets:
            pylog.error(f"Custom Widget with ID {widget_id} already exists in")
            raise KeyError
        self.custom_widgets[widget_id] = widget

    def unregister_custom_widget(self, widget_id: str):
        """ Register Custom Widget """
        if widget_id not in self.custom_widgets:
            pylog.error(f"Custom Widget with ID {widget_id} already exists in")
            raise KeyError
        del self.custom_widgets[widget_id]

    def get(self, plugin_id: str) -> BaseWidget:
        return self._plugins[plugin_id]

    def get_loaded_plugins(self) -> Dict[str, Dict]:
        return self.loaded_plugins

    def _validate_plugin_info(self, farms_info):
        """Validate plugin metadata"""
        required_fields = ["name", "version", "author",]
        optional_fields = ["stage", ]

        for field in required_fields:
            if field not in farms_info:
                return False

        # Validate stage
        valid_stages = ["modeling", "simulation", "analysis"]
        if farms_info["stage"] not in valid_stages:
            pylog.warning(f"Invalid plugin stage {farms_info['stage']}")

        return True

    @staticmethod
    def get_plugin_paths_from_env() -> List:
        """ Get plugin paths from ENV variable FARMS_PLUGIN_PATH """
        env_paths = os.environ.get(FARMS_PLUGIN_ENV, "")
        # If not defined return an empty list
        if not env_paths:
            return []

        # Support both : (Unix) and ; (Windows) separators
        separator = ';' if os.name == 'nt' else ':'
        plugin_paths = env_paths.split(separator)

        return [Path(path.strip()).expanduser().resolve()
                for path in plugin_paths if path.strip()]

    # def resolve_dependencies() -> DependencyGraph:
    #     ...
