""" Main script to run the FARMS app """

import imgui
import imgui.core
import mujoco
import numpy as np
import pyglet
from farms_core import pylog
from imgui import plot as implot
from imgui.integrations.pyglet import PygletRenderer
from pyglet.gl import GL_COLOR_BUFFER_BIT, glClear, glClearColor


class ImguiApp(pyglet.window.Window):

    def __init__(self, **kwargs):
        super().__init__(1280, 720, "MuJoCo-ImGUI", resizable=True)
        pyglet.clock.schedule_interval(self.update, 1 / 60)
        self.background_color_light = (1.0, 1.0, 1.0, 1.0)  # RGBA format
        self.background_color_dark = (0.1, 0.1, 0.1, 1.0)  # RGBA format

        self.mujoco_size = (800, 400)
        self.hdpi_ratio = int(self.get_framebuffer_size()[0]/self.get_size()[0])
        self.viewport = mujoco.MjrRect(0, 0, 0, 0)
        self.viewport.width, self.viewport.height = self.mujoco_size[0]*self.hdpi_ratio, self.mujoco_size[1]*self.hdpi_ratio
        self.texture = pyglet.image.Texture.create_for_size(
            pyglet.gl.GL_TEXTURE_2D, self.mujoco_size[0]*self.hdpi_ratio, self.mujoco_size[1]*self.hdpi_ratio, pyglet.gl.GL_RGB
        )
        self.frame = np.zeros((self.mujoco_size[0]*self.hdpi_ratio * self.mujoco_size[1]*self.hdpi_ratio * 3, 1), dtype=np.uint8)
        # ImGUI
        imgui_context = imgui.create_context()
        _ = implot.create_context()
        implot.set_imgui_context(imgui_context)
        implot.get_style().anti_aliased_lines = True
        self.impl = PygletRenderer(self)
        imgui.new_frame()
        imgui.end_frame()

    def on_draw(self):

        glClearColor(*self.background_color_light)
        glClear(GL_COLOR_BUFFER_BIT)
        self.clear()

        imgui.render()
        self.impl.render(imgui.get_draw_data())
        imgui.new_frame()

        # Draw
        # test
        self.draw_test()
        imgui.set_next_window_position(0, 20)

        imgui.end_frame()

    def update(self, dt):
        """ Update """
        pass

    # Draw
    def draw_test(self):
        with imgui.begin("Test Window"):
            imgui.text("This is the test window.")


def run(**kwargs):
    """ Main entry point to run the GUI """
    pylog.info("Launching FARMS GUI")
    app = ImguiApp()
    pyglet.app.run()
