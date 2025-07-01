"""
Main script to run the FARMS app
"""

from typing import List
# from farms_app.core.options import ApplicationOptions
import numpy as np
from imgui_bundle import imgui, imgui_ctx, implot

import OpenGL.GL as GL  # type: ignore
from farms_app.backends.manager import BackendManager
from farms_app.backends.glfw_impl import OpenGLVersion
from farms_app.plugins.base import BasePlugin
from farms_app.plugins.defaults.simulation import ParameterEditorPlugin
from farms_app.plugins.defaults.logger import LoggerPlugin
from farms_app.plugins.defaults.mujoco_impl import MuJoCoPlugin
from farms_app.plugins.defaults.network import NetworkPlugin
import glfw


class FARMSApplication:
    """FARMS Application """

    def __init__(self, **kwargs):
        """Initialization"""
        super().__init__()
        self.plugins: List[BasePlugin] = []

        manager = BackendManager()
        self.backend = manager.create_backend(backend_type="glfw", gl_version=OpenGLVersion.GL2)
        self.backend.initialize()
        self._window = self.backend.window
        self._io = imgui.get_io()

        self.plugins.append(ParameterEditorPlugin())
        # self.plugins.append(LoggerPlugin())
        self.plugins.append(MuJoCoPlugin())
        # self.plugins.append(NetworkPlugin())

    @classmethod
    def from_options(cls, options):
        """ Initialize using options """
        ...

    def render_plugins(self):
        """Render all plugins"""
        for plugin in self.plugins:
            plugin.render()

    def render_menu(self):
        """ Render menu """
        imgui.begin_main_menu_bar()
        if imgui.begin_menu("File"):
            if imgui.menu_item("New Project", shortcut="N", p_selected=True)[0]:
                print("New project")
            imgui.end_menu()

        if imgui.begin_menu("View"):
            if imgui.menu_item("Plugins", shortcut="C", p_selected=True)[0]:
                print("View")
            imgui.end_menu()
        imgui.end_main_menu_bar()

    def run(self):
        """main run method"""

        while not glfw.window_should_close(self._window):
            glfw.poll_events()

            # Start the Dear ImGui frame
            self.backend.begin_frame()

            self.render_menu()
            imgui.dock_space_over_viewport()
            self.render_plugins()

            self.backend.end_frame()

        # Cleanup
        self.backend.cleanup()


def main():
    """ main """
    app = FARMSApplication()
    app.run()


if __name__ == '__main__':
    main()
