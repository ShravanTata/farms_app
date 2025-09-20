""" Window """


from abc import ABC, abstractmethod
from farms_app.extensions.base import BaseExtension

from imgui_bundle import imgui


class BaseWindow(ABC):
    """ Base Window """

    def __init__(
            self, name: str, extension: BaseExtension, window_flags: imgui.WindowFlags_=imgui.WindowFlags_.none
    ):
        "Initialise"

        self.name: str = name
        self.extension: BaseExtension = extension
        self.window_id: str = self.create_window_id(self.extension, self.name)
        self.window_flags: imgui.WindowFlags_ = window_flags

    def _render(self):
        """ Internal main render call """
        if imgui.begin(self.window_id, flags=self.window_flags):
            self.render_content()
        imgui.end()

    @abstractmethod
    def render_content(self):
        """ Render content for the window """
        pass

    def set_window_flags(self, window_flags: imgui.WindowFlags_):
        """ Set ImGUI window flags """
        pass

    def validate_window(self, extension_manager):
        """ Validate that window belongs to one of the loaded available extensions """
        pass

    def create_window_id(self, name: str, extension: str) -> str:
        """ Useful for creating extension specific window names """
        return f"{extension}##{name}"
