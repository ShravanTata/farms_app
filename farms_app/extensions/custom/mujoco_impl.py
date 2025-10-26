""" MuJoCo """

import ctypes

import mujoco
import numpy as np
import OpenGL.GL as GL  # type: ignore
from farms_core import pylog
from imgui_bundle import imgui

from farms_app.core.extension import CustomExtension
from imgui_bundle import portable_file_dialogs as pfd
from farms_app.core.window import BaseWindow


MJ_IMGUI_KEYMAP = {
    # special keys
    "/": imgui.Key.slash,
    "\\": imgui.Key.backslash,
    ",": imgui.Key.comma,
    ".": imgui.Key.period,
    ";": imgui.Key.semicolon,
    "'": imgui.Key.apostrophe,
    "[": imgui.Key.left_bracket,
    "]": imgui.Key.right_bracket,
    "-": imgui.Key.minus,
    "=": imgui.Key.equal,
    "`": imgui.Key.grave_accent,
    # letters A–Z
    **{chr(c): getattr(imgui.Key, chr(c).lower()) for c in range(ord("A"), ord("Z")+1)},
    **{str(i): getattr(imgui.Key, f"_{i}") for i in range(6)},
}


_mjGEOMSTRING = (
    (
        "Geom1", "1", "0",
        "Geom2", "1", "1",
        "Geom3", "1", "2",
        "Geom4", "0", "3",
        "Geom5", "0", "4",
        "Geom6", "0", "5",
    ),
)


class MuJoCoWindow(BaseWindow):
    """ MuJoCo Window """

    def __init__(self, extension):
        name: str = "MuJoCo"
        super().__init__(name, extension)
        self._io = imgui.get_io()
        self.model = None
        self.data = None

    def on_initialize(self):
        """ Initialize """

    def on_render(self):
        """ Render main extension dockspace """
        if self.data is not None and self.model is not None:
            self.run_simulation()
            imgui.button("Play")
        else:
            if imgui.button("Load mjcf"):
                self.result = pfd.open_file("Load MJCF", default_path="", filters=("*.xml",),).result()
                if self.result:
                    self.model = mujoco.MjModel.from_xml_path(self.result[0])
                    self.data = mujoco.MjData(self.model)
                    self.setup_simulation()

    def setup_simulation(self):
        self.camera = mujoco.MjvCamera()
        self.option = mujoco.MjvOption()
        self.option.flags[mujoco.mjtVisFlag.mjVIS_LIGHT] = True
        self.model.vis.headlight.ambient[:] = [0.6]*3
        self.model.vis.headlight.diffuse[:] = [0.4]*3
        self.model.vis.headlight.specular[:] = [0.5]*3
        self.perturb = mujoco.MjvPerturb()
        mujoco.mjv_defaultCamera(self.camera)
        mujoco.mjv_defaultPerturb(self.perturb)
        mujoco.mjv_defaultOption(self.option)
        self.mj_context = mujoco.MjrContext(self.model, mujoco.mjtFontScale.mjFONTSCALE_150)
        self.scene = mujoco.MjvScene(self.model, maxgeom=1000000)

        self.viewport = mujoco.MjrRect(0, 0, 0, 0)
        self.width, self.height = 1280, 720
        self.max_width, self.max_height = 1920, 1080
        self.viewport.width, self.viewport.height = self.width, self.height
        self.framebuffer = None
        self.depth_buffer = None
        self.texture_id = None
        self.create_framebuffer(self.width, self.height)

        self.start_time = self.data.time

    def create_framebuffer(self, width: int, height: int):
        """ Create Framebuffer """
        self.texture_id = GL.glGenTextures(1)

        GL.glBindTexture(GL.GL_TEXTURE_2D, self.texture_id)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA, width, height, 0,
                        GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, None)
        # Set texture parameters
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)

        # Create framebuffer
        self.framebuffer = GL.glGenFramebuffers(1)
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.framebuffer)

        # Attach texture to framebuffer
        GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER, GL.GL_COLOR_ATTACHMENT0,
                                  GL.GL_TEXTURE_2D, self.texture_id, 0)

        # Create depth buffer
        self.depth_buffer = GL.glGenRenderbuffers(1)
        GL.glBindRenderbuffer(GL.GL_RENDERBUFFER, self.depth_buffer)
        GL.glRenderbufferStorage(GL.GL_RENDERBUFFER, GL.GL_DEPTH_COMPONENT24,
                                 self.width, self.height)
        GL.glFramebufferRenderbuffer(GL.GL_FRAMEBUFFER, GL.GL_DEPTH_ATTACHMENT,
                                    GL.GL_RENDERBUFFER, self.depth_buffer)

        # Check framebuffer completeness
        if GL.glCheckFramebufferStatus(GL.GL_FRAMEBUFFER) != GL.GL_FRAMEBUFFER_COMPLETE:
            pylog.error("Framebuffer not complete!")

        # GL.glEnable(GL.GL_MULTISAMPLE)

        # unbind framebuffer
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)

    def resize_framebuffer(self, width, height):
        # Delete old OpenGL resources
        GL.glDeleteTextures([self.texture_id])
        GL.glDeleteRenderbuffers(1, [self.depth_buffer])
        GL.glDeleteFramebuffers(1, [self.framebuffer])

        # Recreate them with new size
        self.viewport.width, self.viewport.height = width, height

        self.create_framebuffer(self.width, self.height)

    def run_simulation(self):
        """ Run Simulation """
        self.start_time = self.data.time
        while (self.data.time - self.start_time < 1.0/60.0):
            mujoco.mj_step(self.model, self.data)

        avail = imgui.get_content_region_avail()
        render_w, render_h = int(avail.x), int(avail.y)

        # Bind framebuffer
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.framebuffer)
        GL.glViewport(0, 0, self.width, self.height)
        self.viewport.width = self.width
        self.viewport.height = self.height
        # update MuJoCo camera aspect

        # Minimal OpenGL setup - let MuJoCo handle lighting
        # GL.glEnable(GL.GL_DEPTH_TEST)
        # GL.glEnable(GL.GL_FRAMEBUFFER_SRGB)
        GL.glClearColor(0.1, 0.1, 0.1, 1.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)

        # Update and render
        mujoco.mjv_updateScene(self.model, self.data, self.option, None, self.camera,
                              mujoco.mjtCatBit.mjCAT_ALL, self.scene)
        mujoco.mjr_render(self.viewport, self.scene, self.mj_context)
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
        # GL.glDisable(GL.GL_FRAMEBUFFER_SRGB)

        target_aspect = self.width / self.height
        avail_width, avail_height = imgui.get_content_region_avail()
        if avail_width <= 0 or avail_height <= 0:
            # Skip rendering this frame or use fallback size
            return
        current_aspect = avail_width / avail_height
        if current_aspect > target_aspect:
            # Window is too wide → limit width
            draw_height = avail_height
            draw_width = target_aspect * draw_height
        else:
            # Window is too tall → limit height
            draw_width = avail_width
            draw_height = draw_width / target_aspect

        imgui.image_with_bg(
            imgui.ImTextureRef(self.texture_id),
            imgui.ImVec2((self.width, self.height)),
            uv0=imgui.ImVec2((1,1)),
            uv1=imgui.ImVec2((0,0)),
            bg_col=imgui.ImVec4((0, 0, 1, 1))
        )

        if imgui.is_item_hovered():
            self.mouse_iteractions()
            self.keyboard_interactions()

    def __mj_keys(self, mjSTRING: tuple[str, str, str], mj_flags):
        for j, _opt in enumerate(mjSTRING):
            key_str = _opt[2]
            if not key_str:
                continue        # Skip if no key assigned
            key_enum = MJ_IMGUI_KEYMAP.get(key_str)
            if key_enum is None:
                continue
            if imgui.is_key_pressed(key_enum):
                mj_flags[j] = not mj_flags[j]

    def keyboard_interactions(self):
        """ keyboard interactions """
        self.__mj_keys(mujoco.mjRNDSTRING, self.scene.flags)
        self.__mj_keys(mujoco.mjVISSTRING, self.option.flags)
        self.__mj_keys(_mjGEOMSTRING, self.option.geomgroup)

    def mouse_iteractions(self):
        """ Mouse interactions """
        mouse_pos = self._io.mouse_pos
        mouse_delta = self._io.mouse_delta
        mouse_wheel = self._io.mouse_wheel
        if imgui.is_key_down(imgui.Key.mouse_left):
            mujoco.mjv_moveCamera(
                self.model,
                mujoco.mjtMouse.mjMOUSE_ROTATE_H,
                -mouse_delta.x / self.width,
                0.0,
                self.scene,
                self.camera,
            )
            mujoco.mjv_moveCamera(
                self.model,
                mujoco.mjtMouse.mjMOUSE_ROTATE_V,
                0.0,
                mouse_delta.y / self.height,
                self.scene,
                self.camera,
            )
        elif imgui.is_key_down(imgui.Key.mouse_right):
            mujoco.mjv_moveCamera(
                self.model,
                mujoco.mjtMouse.mjMOUSE_MOVE_H,
                -mouse_delta.x / self.width,
                0.0,
                self.scene,
                self.camera,
            )
            mujoco.mjv_moveCamera(
                self.model,
                mujoco.mjtMouse.mjMOUSE_MOVE_V,
                0.0,
                mouse_delta.y / self.height,
                self.scene,
                self.camera,
            )
        elif imgui.is_key_down(imgui.Key.mouse_wheel_y):
            mujoco.mjv_moveCamera(
                self.model,
                mujoco.mjtMouse.mjMOUSE_ZOOM,
                0.0,
                np.sign(mouse_wheel)*0.05*1,
                self.scene,
                self.camera,
            )


class MujocoExtension(CustomExtension):
    """ MuJoCo """

    def __init__(self):
        super().__init__(name="MuJoCo")
        self.hide = False

        # Register windows
        self.register_window(MuJoCoWindow(self))

    def __del__(self):
        print("Terminating MuJoCo Extension")

    def get_name(self) -> str:
        return "MuJoCo"

    def cleanup(self):
        pass

    def get_dependencies(self):
        pass
