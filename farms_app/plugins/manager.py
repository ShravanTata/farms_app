""" Plugin Manager """

import importlib
from typing import Dict, List, Union

from farms_core import pylog

from .base import BasePlugin, AppPlugin, FarmsPlugin, CustomPlugin
from ..utils.paths import get_project_root


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

        # Three different types of Plugins
        self._plugins = {}
        self.app_plugins = {}
        self.farms_plugins = {}
        self.custom_plugins = {}

    def register(
            self, name: str, plugin: Union[AppPlugin, FarmsPlugin, CustomPlugin]
    ):
        """ Register plugin """
        if isinstance(plugin, AppPlugin):
            self.register_app_plugin(name, plugin)
        elif isinstance(plugin, FarmsPlugin):
            self.register_farms_plugin(name, plugin)
        elif isinstance(plugin, CustomPlugin):
            self.register_custom_plugin(name, plugin)
        else:
            pylog.error(f"Unknown Plugin {type(plugin)} type with ID {name}")
            # raise TypeError
        self._plugins[name] = plugin

    def register_app_plugin(self, name: str, plugin: AppPlugin):
        """ Register App Plugin """
        if name in self.app_plugins:
            pylog.error(f"App Plugin with ID {name} already exists in")
            raise KeyError
        self.app_plugins[name] = plugin

    def register_farms_plugin(self, name: str, plugin: FarmsPlugin):
        """ Register Farms Plugin """
        if name in self.farms_plugins:
            pylog.error(f"Farms Plugin with ID {name} already exists in")
            raise KeyError
        self.farms_plugins[name] = plugin

    def register_custom_plugin(self, name: str, plugin: CustomPlugin):
        """ Register Custom Plugin """
        if name in self.custom_plugins:
            pylog.error(f"Custom Plugin with ID {name} already exists in")
            raise KeyError
        self.custom_plugins[name] = plugin

    def get(self, plugin_id: str) -> BasePlugin:
        return self._plugins[plugin_id]

    def _discover_user_plugins(self):
        """Scan user plugins directory"""
        user_dir = get_project_root().joinpath("farms_app", "plugins", "defaults")
        pylog.debug(user_dir)
        if not user_dir.exists():
            return

        for plugin_file in user_dir.glob("*.py"):
            pylog.debug(f"{plugin_file}")
            if plugin_file.name.startswith("_"):
                continue  # Skip private files

            try:
                pass
                plugin_info = self._load_plugin_file(plugin_file)
                if plugin_info:
                    plugin_id = plugin_file.stem
                    self.user_plugins[plugin_id] = plugin_info
            except Exception as e:
                pylog.warning(f"Failed to load plugin {plugin_file}: {e}")

    def _load_plugin_file(self, plugin_file):
        """Load a single plugin file"""
        # Dynamic import
        spec = importlib.util.spec_from_file_location(
            plugin_file.stem, plugin_file
        )
        module = importlib.util.module_from_spec(spec)
        # if (mod_file := mod.__file__) is None:

        # Execute the module
        spec.loader.exec_module(module)

        # Check for farms_info
        if not hasattr(module, 'farms_info'):
            pylog.warning(f"Plugin {plugin_file} missing farms_info")
            return None

        # Validate metadata
        farms_info = module.farms_info
        if not self._validate_plugin_info(farms_info):
            return None

        # Find plugin class (look for BasePlugin subclass)
        plugin_class = self._find_plugin_class(module)
        if not plugin_class:
            return None

        # Create instance
        return plugin_class()

    def _validate_plugin_info(self, farms_info):
        """Validate plugin metadata"""
        required_fields = ["name", "stage", "version", "author"]

        for field in required_fields:
            if field not in farms_info:
                return False

        # Validate stage
        valid_stages = ["modeling", "simulation", "analysis"]
        if farms_info["stage"] not in valid_stages:
            pylog.error(f"Invalid plugin stage {farms_info['stage']}")
            return False

        return True

    # def discover_plugins() -> List[PluginInfo]:
    #     ...

    # def load_plugin(plugin_id: str) -> BasePlugin:
    #     ...

    # def unload_plugin(plugin_id: str) -> bool:
    #     ...

    # def resolve_dependencies() -> DependencyGraph:
    #     ...

    def get_loaded_plugins(self) -> Dict[str, BasePlugin]:
        return self._plugins
