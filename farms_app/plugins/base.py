""" Base class implementation for plugin system """


from abc import ABC, abstractmethod
from imgui_bundle import imgui


class BasePlugin(ABC):
    """Plugin base class"""

    def __init__(self):
        ""
        super().__init__()
        self.show_window = True
        self.window_name = "Plugin"
        self.stage = None

    @abstractmethod
    def get_name(self) -> str:
        pass

    # @abstractmethod
    # def get_info() -> PluginInfo:
    #     pass

    # @abstractmethod
    # def get_dependencies() -> List[str]:
    #     pass

    # @abstractmethod
    # def initialize(context: AppContext) -> bool:
    #     pass

    # @abstractmethod
    # def enable() -> bool:
    #     pass

    # @abstractmethod
    # def disable() -> bool:
    #     pass

    # @abstractmethod
    # def reload() -> bool:
    #     pass

    # @abstractmethod
    # def update(delta_time: float) -> None:
    #     pass

    def render_window(self):
        if not self.show_window:
            return

        expanded, self.show_window = imgui.begin(self.window_name, self.show_window)
        if expanded:
            self.render()
        imgui.end()

    @abstractmethod
    def render() -> None:
        pass

    # @abstractmethod
    # def cleanup() -> None:
    #     pass
