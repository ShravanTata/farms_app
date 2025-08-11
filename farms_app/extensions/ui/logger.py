""" Logger """

from colorama import Fore
from farms_core import pylog
from imgui_bundle import imgui

from farms_app.plugins.base import CustomPlugin

ANSI_RGB_MAP = {
    Fore.CYAN: (0, 1.0, 1.0, 1.0),
    Fore.GREEN: (0, 1.0, 0, 1.0),
    Fore.YELLOW: (1.0, 1.0, 0, 1.0),
    Fore.RED: (1.0, 0, 0, 1.0),
    Fore.MAGENTA: (1.0, 0, 1.0, 1.0),
}


farms_info = {
    "name": "Logger Plugin",
    "stage": "",
    "version": (0, 0, 1),
    "author": "FARMS"
}


class LoggerPlugin(CustomPlugin):
    """ Logger """

    def __init__(self):
        self.show_window = True
        self.window_name = "Logger"

    def get_name(self) -> str:
        return "Logger"

    def render(self) -> None:
        if imgui.begin_popup("Options"):
            imgui.checkbox("Auto-scroll", True)
            imgui.end_popup()

        # Main window
        if imgui.button("Options"):
            imgui.open_popup("Options")
        imgui.same_line()
        clear = imgui.button("Clear")
        imgui.same_line()
        copy = imgui.button("Copy")
        # ImGui::SameLine();
        # Filter.Draw("Filter", -100.0f);

        if imgui.begin_child("scrolling", imgui.ImVec2((0, 0)), imgui.ChildFlags_.none, imgui.WindowFlags_.horizontal_scrollbar):
            # for color, line in pylog.LOGGER.get_gui_logs():
            #      imgui.text_colored(imgui.ImVec4(*ANSI_RGB_MAP.get(color)), line)
            imgui.text("Hello world!")
        imgui.end_child()


def register(plugin_manager):
    """ Register """
    plugin_manager.register_class(LoggerPlugin)


def unregister(plugin_manager):
    """ Unregister """
    plugin_manager.unregister_class(LoggerPlugin)
