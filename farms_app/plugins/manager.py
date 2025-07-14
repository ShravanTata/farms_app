""" Plugin Manager """

from typing import Dict, List

from farms_core import pylog

from .base import BasePlugin


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
        self._plugins = {}

    def register(self, plugin_id: str, plugin: BasePlugin):
        """ Register plugin """
        if plugin_id in self._plugins:
            pylog.error(f"Plugin with ID {plugin_id} already exists")
            raise KeyError
        self._plugins[plugin_id] = plugin

    def get(self, plugin_id: str) -> BasePlugin:
        return self._plugins[plugin_id]

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
