""" Base class implementation for application extension system """


import time
from abc import ABC, abstractmethod

from imgui_bundle import imgui


class BaseExtension(ABC):
    """Extension base  class"""

    farms_name = "Base"
    farms_stage = ""
    farms_version = ""
    farms_author = ""

    def __init__(self):
        ""
        super().__init__()
        self.show_window: bool = True
        self.window_name = "Base Widget"
        self.stage = None
        self.performance_warnings = []

    # @abstractmethod
    # def initialize(context: AppContext) -> bool:
    #     pass

    @abstractmethod
    def render(self) -> None:
        pass

    # @abstractmethod
    # def cleanup() -> None:
    #     pass

    def get_info():
        pass

    def _render_with_timing(self):
        start_time = time.perf_counter()

        try:
            self.render()
        except Exception as e:
            imgui.text_colored((1, 0, 0, 1), f"Widget Error: {e}")
            return

        render_time = time.perf_counter() - start_time

        # Warn about slow renders
        if render_time > 0.03:  # 0.03 = 30fps threshold
            warning = f"Slow render: {render_time*1000:.1f}ms"
            self.performance_warnings.append(warning)
            print(f"⚠️  Widget '{self.window_name}': {warning}")

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

    # @abstractmethod
    # def get_name(self) -> str:
    #     pass

    # @abstractmethod
    # def get_dependencies() -> List[str]:
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


class UIExtension(BaseExtension):
    """Full access - internal app components like status bar, menu bar"""
    def __init__(self, app_context):
        super().__init__()
        self.app_context = app_context  # Full access


class WorkflowExtension(BaseExtension):
    """FARMS data access - simulation, analysis plugins"""
    def __init__(self):
        super().__init__()
        self.farms_data = None  # Set by plugin manager

    def render(self):
        if not self.show_window:
            return

        expanded, _ = imgui.begin(
            self.window_name, self.show_window, flags=imgui.WindowFlags_.menu_bar
        )
        if expanded:
            self.render_window()
        imgui.end()

    @abstractmethod
    def render_window(self):
        pass


class CustomExtension(BaseExtension):
    """No special access - user experiments, visualizations"""
    def __init__(self):
        super().__init__()
        # No special data access

    def render(self):
        if not self.show_window:
            return

        expanded, _ = imgui.begin(
            self.window_name, self.show_window, flags=imgui.WindowFlags_.menu_bar
        )
        if expanded:
            self.render_window()
        imgui.end()

    @abstractmethod
    def render_window(self):
        pass
