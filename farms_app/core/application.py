"""
Main script to run the FARMS app
"""

from typing import List
from farms_app.core.options import ApplicationOptions
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
        self.plugins.append(LoggerPlugin())
        self.plugins.append(MuJoCoPlugin())
        self.plugins.append(NetworkPlugin())

    @classmethod
    def from_options(cls, options: ApplicationOptions):
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

        self.clear_color = [0.45, 0.55, 0.60, 1.00]
        GL.glEnable(GL.GL_MULTISAMPLE)

        while not glfw.window_should_close(self._window):
            glfw.poll_events()

            # Start the Dear ImGui frame
            self.backend.begin_frame()

            self.render_menu()
            imgui.dock_space_over_viewport()
            self.render_plugins()

            # 3. Show another simple window.
            def gui_another_window(name) -> None:
                imgui.begin(
                    name,
                    # flags=(
                    #     imgui.WindowFlags_.no_collapse |
                    #     imgui.WindowFlags_.no_move
                    # ),
                )  # Pass a pointer to our bool variable (the window will have a closing button that will clear the bool when clicked)
                imgui.text("Hello from another window!")
                _, self.clear_color = imgui.color_edit4(
                    "clear color", self.clear_color
                )  # Edit 4 floats representing a c
                imgui.end()

            # imgui.dock_space(dockspace_id=1)
            # imgui.set_next_window_pos((0.0, 0.0))

            imgui.begin(
                "Win",
                    flags=(
                        imgui.WindowFlags_.menu_bar
                        # imgui.WindowFlags_.no_collapse |
                        # imgui.WindowFlags_.no_move
                    ),
            )  # Pass a pointer to our bool variable (the window will have a closing button that will clear the bool when clicked)
            imgui.begin_menu_bar()
            if imgui.begin_menu("New"):
                imgui.menu_item("Test", "T", p_selected=False)
                imgui.end_menu()
            imgui.end_menu_bar()
            imgui.text("Hello from another window!")
            imgui.end()
            # imgui.set_next_window_size(self._io.display_size)
            gui_another_window(name="Simulation")
            # imgui.set_next_window_size(self._io.display_size)
            # imgui.set_next_window_dock_id
            gui_another_window(name="Network")

            imgui.render()
            display_w, display_h = glfw.get_framebuffer_size(self._window)
            GL.glViewport(0, 0, display_w, display_h)
            GL.glClearColor(
                self.clear_color[0] * self.clear_color[3],
                self.clear_color[1] * self.clear_color[3],
                self.clear_color[2] * self.clear_color[3],
                self.clear_color[3],
            )
            GL.glClear(GL.GL_COLOR_BUFFER_BIT)
            self.backend.draw(imgui.get_draw_data())

            # Update and Render additional Platform Windows
            # (Platform functions may change the current OpenGL context, so we save/restore it to make it easier to paste this code elsewhere.
            #  For this specific demo app we could also call glfwMakeContextCurrent(self._window) directly)
            if self._io.config_flags & imgui.ConfigFlags_.viewports_enable.value > 0:
                backup_current_context = glfw.get_current_context()
                imgui.update_platform_windows()
                imgui.render_platform_windows_default()
                glfw.make_context_current(backup_current_context)

            glfw.swap_buffers(self._window)

        # Cleanup
        # imgui.backends.opengl3_shutdown()
        imgui.backends.glfw_shutdown()
        imgui.destroy_context()

        glfw.destroy_window(self._window)
        glfw.terminate()


def main():
    """ main """
    app = FARMSApplication()
    app.run()


if __name__ == '__main__':
    main()
