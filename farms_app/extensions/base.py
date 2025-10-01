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
        self.name: str = "Name"
        self.stage = None
        self.performance_warnings = []
        self.windows = []

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

    def create_window_id(self, name: str) -> str:
        """ Useful for creating extension specific window names """
        return f"{self.window_name}##{name}"

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
    """
    Full app interface access.
    Can modify menus, toolbars, status bars, and global UI.
    """
    def __init__(self):
        super().__init__()
        self.app_context = None  # Full access


class WorkflowExtension(BaseExtension):
    """
    FARMS domain access.
    Can read/write simulation data, add workflow windows.
    """
    def __init__(self):
        super().__init__()
        self.farms_data = None  # Set by plugin manager
        self.is_focused = False

    def render_menu(self):
        """ Render menu """
        imgui.begin_main_menu_bar()

        if imgui.begin_menu(f"{self.window_name}"):
            imgui.text("Hello")
            imgui.end_menu()
        imgui.end_main_menu_bar()

    def render(self):
        if not self.show_window:
            return

        expanded, _ = imgui.begin(
            self.window_name, self.show_window, flags=imgui.WindowFlags_.menu_bar
        )
        if expanded:
            self.is_focused = imgui.is_window_focused(imgui.FocusedFlags_.root_and_child_windows)
            self.render_window()
            self.is_focused = imgui.is_window_focused(imgui.FocusedFlags_.root_and_child_windows)
        imgui.end()

    @abstractmethod
    def render_window(self):
        pass


class CustomExtension(BaseExtension):
    """
    Independent / standalone extensions.
    Minimal host context; no FARMS data required.
    user experiments, visualizations, no communication between extensions
    """
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
