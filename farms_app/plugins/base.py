""" Base class implementation for plugin system """


import time
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
        self.performance_warnings = []

    @abstractmethod
    def get_name(self) -> str:
        pass

    def get_info():
        pass

    def render_window(self):
        if not self.show_window:
            return

        expanded, self.show_window = imgui.begin(
            self.window_name, self.show_window, flags=imgui.WindowFlags_.menu_bar
        )
        if expanded:
            self._render_with_timing()
        imgui.end()

    def _render_with_timing(self):
        start_time = time.perf_counter()

        try:
            self.render()
        except Exception as e:
            imgui.text_colored((1, 0, 0, 1), f"Plugin Error: {e}")
            return

        render_time = time.perf_counter() - start_time

        # Warn about slow renders
        if render_time > 0.03:  # 0.03 = 30fps threshold
            warning = f"Slow render: {render_time*1000:.1f}ms"
            self.performance_warnings.append(warning)
            print(f"⚠️  Plugin '{self.window_name}': {warning}")

        # Show warnings in GUI
        # self._show_performance_warnings()

    def _show_performance_warnings(self):
        if self.performance_warnings:
            imgui.separator()
            imgui.text_colored((1, 1, 0, 1), "⚠️ Performance Warnings:")
            for warning in self.performance_warnings[-3:]:  # Show last 3
                imgui.text_colored((1, 1, 0, 1), f"  {warning}")

            if imgui.button("Clear Warnings"):
                self.performance_warnings.clear()

    @abstractmethod
    def render(self) -> None:
        pass

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

    # @abstractmethod
    # def cleanup() -> None:
    #     pass


class AppPlugin(BasePlugin):
    """Full access - internal app components like status bar, menu bar"""
    def __init__(self, app_context):
        super().__init__()
        self.app_context = app_context  # Full access

    @abstractmethod
    def render(self):
        pass


class FarmsPlugin(BasePlugin):
    """FARMS data access - simulation, analysis plugins"""
    def __init__(self):
        super().__init__()
        self.farms_data = None  # Set by plugin manager

    @abstractmethod
    def render(self):
        pass


class CustomPlugin(BasePlugin):
    """No special access - user experiments, visualizations"""
    def __init__(self):
        super().__init__()
        # No special data access

    @abstractmethod
    def render(self):
        pass
