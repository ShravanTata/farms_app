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

    def __init__(self, extension, window_size = (1280, 720)):
        name: str = "MuJoCo"
        super().__init__(name, extension)
        self._io = imgui.get_io()
        self.model = None
        self.data = None
        self.width, self.height = window_size[0], window_size[1]

        self.framebuffer = None
        self.depth_buffer = None
        self.texture_id = None

        # MjScene
        self.mj_camera = None
        self.mj_option = None
        self.mj_perturb = None
        self.mj_viewport = None
        self.mj_scene = None

        self.is_scene_hovered = False

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
                    # Setup mujoco scene
                    self.setup_mj_scene()

                    (self.msaa_fbo,
                     self.resolve_fbo,
                     self.resolve_texture,
                     self.msaa_color_rb,
                     self.msaa_depth_rb) = MuJoCoWindow.create_framebuffer(self.width, self.height, 4)

    def setup_mj_scene(self):
        self.mj_camera = mujoco.MjvCamera()
        self.mj_option = mujoco.MjvOption()
        self.mj_option.flags[mujoco.mjtVisFlag.mjVIS_LIGHT] = True
        self.model.vis.headlight.ambient[:] = [0.6]*3
        self.model.vis.headlight.diffuse[:] = [0.4]*3
        self.model.vis.headlight.specular[:] = [0.5]*3
        self.mj_perturb = mujoco.MjvPerturb()
        mujoco.mjv_defaultCamera(self.mj_camera)
        mujoco.mjv_defaultPerturb(self.mj_perturb)
        mujoco.mjv_defaultOption(self.mj_option)
        self.mj_context = mujoco.MjrContext(self.model, mujoco.mjtFontScale.mjFONTSCALE_150)
        mujoco.mjr_setBuffer(mujoco.mjtFramebuffer.mjFB_OFFSCREEN, self.mj_context)  # <-- added
        self.mj_scene = mujoco.MjvScene(self.model, maxgeom=1000000)
        self.mj_viewport = mujoco.MjrRect(0, 0, 0, 0)
        self.mj_viewport.width, self.mj_viewport.height = self.width, self.height


    @staticmethod
    def create_framebuffer(width: int, height: int, samples: int = 4):
        """
        Create MSAA framebuffer for MuJoCo rendering + resolve framebuffer for ImGui.
        Returns:
        msaa_fbo, resolve_fbo, resolve_texture, msaa_color_rb, msaa_depth_rb
        """

        # -------------------------
        # MSAA framebuffer (render target)
        # -------------------------
        msaa_fbo = GL.glGenFramebuffers(1)
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, msaa_fbo)

        # Multisampled color renderbuffer
        msaa_color_rb = GL.glGenRenderbuffers(1)
        GL.glBindRenderbuffer(GL.GL_RENDERBUFFER, msaa_color_rb)
        GL.glRenderbufferStorageMultisample(
            GL.GL_RENDERBUFFER,
            samples,
            GL.GL_RGBA8,
            width,
            height,
        )
        GL.glFramebufferRenderbuffer(
            GL.GL_FRAMEBUFFER,
            GL.GL_COLOR_ATTACHMENT0,
            GL.GL_RENDERBUFFER,
            msaa_color_rb,
        )

        # Multisampled depth renderbuffer
        msaa_depth_rb = GL.glGenRenderbuffers(1)
        GL.glBindRenderbuffer(GL.GL_RENDERBUFFER, msaa_depth_rb)
        GL.glRenderbufferStorageMultisample(
            GL.GL_RENDERBUFFER,
            samples,
            GL.GL_DEPTH_COMPONENT24,
            width,
            height,
        )
        GL.glFramebufferRenderbuffer(
            GL.GL_FRAMEBUFFER,
            GL.GL_DEPTH_ATTACHMENT,
            GL.GL_RENDERBUFFER,
            msaa_depth_rb,
        )

        if GL.glCheckFramebufferStatus(GL.GL_FRAMEBUFFER) != GL.GL_FRAMEBUFFER_COMPLETE:
            raise RuntimeError("MSAA framebuffer is not complete")

        # -------------------------
        # Resolve framebuffer (texture for ImGui)
        # -------------------------
        resolve_fbo = GL.glGenFramebuffers(1)
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, resolve_fbo)

        resolve_texture = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, resolve_texture)

        GL.glTexImage2D(
            GL.GL_TEXTURE_2D,
            0,
            GL.GL_RGBA8,       # was GL_SRGB8_ALPHA8
            width,
            height,
            0,
            GL.GL_RGBA,
            GL.GL_UNSIGNED_BYTE,
            None,
        )

        # Use nearest to avoid ImGui-induced blur
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_NEAREST)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_NEAREST)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)

        GL.glFramebufferTexture2D(
            GL.GL_FRAMEBUFFER,
            GL.GL_COLOR_ATTACHMENT0,
            GL.GL_TEXTURE_2D,
            resolve_texture,
            0,
        )

        if GL.glCheckFramebufferStatus(GL.GL_FRAMEBUFFER) != GL.GL_FRAMEBUFFER_COMPLETE:
            raise RuntimeError("Resolve framebuffer is not complete")

        # Unbind
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
        GL.glBindRenderbuffer(GL.GL_RENDERBUFFER, 0)
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)

        return (
            msaa_fbo,
            resolve_fbo,
            resolve_texture,
            msaa_color_rb,
            msaa_depth_rb,
        )

    def resize_framebuffer(self, width, height):
        # Delete old OpenGL resources
        GL.glDeleteTextures([self.texture_id])
        GL.glDeleteRenderbuffers(1, [self.depth_buffer])
        GL.glDeleteFramebuffers(1, [self.framebuffer])

        # Recreate them with new size
        self.mj_viewport.width, self.mj_viewport.height = width, height

        # self.framebuffer, self.texture_id, self.depth_buffer = MuJoCoWindow.create_framebuffer(
        #     self.width, self.height
        # )
        (self.msaa_fbo,
        self.resolve_fbo,
        self.resolve_texture,
        self.msaa_color_rb,
        self.msaa_depth_rb) = MuJoCoWindow.create_framebuffer(self.width, self.height)

    def run_simulation(self):
        """ Run Simulation """
        self.start_time = self.data.time
        while (self.data.time - self.start_time < 1.0/60.0):
            mujoco.mj_step(self.model, self.data)

        avail = imgui.get_content_region_avail()
        render_w, render_h = int(avail.x), int(avail.y)

        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.msaa_fbo)
        GL.glViewport(0, 0, self.width, self.height)

        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glClearColor(1.0, 1.0, 1.0, 1.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)

        mujoco.mjv_updateScene(
            self.model, self.data, self.mj_option, None, self.mj_camera,
            mujoco.mjtCatBit.mjCAT_ALL, self.mj_scene
        )
        mujoco.mjr_render(self.mj_viewport, self.mj_scene, self.mj_context)

        try:
            GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
        except GL.GLError:
            pass

        GL.glDisable(GL.GL_DEPTH_TEST)

        # Blit MSAA -> resolve (no sRGB toggling, nearest filter for 1:1 blit)
        GL.glBindFramebuffer(GL.GL_READ_FRAMEBUFFER, self.msaa_fbo)
        GL.glBindFramebuffer(GL.GL_DRAW_FRAMEBUFFER, self.resolve_fbo)
        GL.glBlitFramebuffer(
            0, 0, self.width, self.height,
            0, 0, self.width, self.height,
            GL.GL_COLOR_BUFFER_BIT,
            GL.GL_NEAREST,  # was GL_LINEAR
        )
        try:
            # Exception handling necessary for Nvidia + Wayland
            GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
        except GL.GLError:
            pass
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

        imgui.image(
            imgui.ImTextureRef(self.resolve_texture),
            imgui.ImVec2((draw_width, draw_height)),
            uv0=imgui.ImVec2((1, 1)),
            uv1=imgui.ImVec2((0, 0)),
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
        self.__mj_keys(mujoco.mjRNDSTRING, self.mj_scene.flags)
        self.__mj_keys(mujoco.mjVISSTRING, self.mj_option.flags)
        self.__mj_keys(_mjGEOMSTRING, self.mj_option.geomgroup)

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
                self.mj_scene,
                self.mj_camera,
            )
            mujoco.mjv_moveCamera(
                self.model,
                mujoco.mjtMouse.mjMOUSE_ROTATE_V,
                0.0,
                mouse_delta.y / self.height,
                self.mj_scene,
                self.mj_camera,
            )
        elif imgui.is_key_down(imgui.Key.mouse_right):
            mujoco.mjv_moveCamera(
                self.model,
                mujoco.mjtMouse.mjMOUSE_MOVE_H,
                -mouse_delta.x / self.width,
                0.0,
                self.mj_scene,
                self.mj_camera,
            )
            mujoco.mjv_moveCamera(
                self.model,
                mujoco.mjtMouse.mjMOUSE_MOVE_V,
                0.0,
                mouse_delta.y / self.height,
                self.mj_scene,
                self.mj_camera,
            )
        elif imgui.is_key_down(imgui.Key.mouse_wheel_y):
            mujoco.mjv_moveCamera(
                self.model,
                mujoco.mjtMouse.mjMOUSE_ZOOM,
                0.0,
                np.sign(mouse_wheel)*0.05*1,
                self.mj_scene,
                self.mj_camera,
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
