""" MuJoCo """


import ctypes

import mujoco
import numpy as np
import OpenGL.GL as GL  # type: ignore
from farms_core import pylog
from imgui_bundle import imgui

from farms_app.extensions.base import CustomExtension

model = mujoco.MjModel.from_xml_string(
"""<mujoco model="2-link 6-muscle arm">
  <option timestep="0.005" iterations="50" solver="Newton" tolerance="1e-10"/>

  <size njmax="50" nconmax="10" nstack="200"/>

  <visual>
    <rgba haze=".8 .8 .8 1"/>
    <headlight ambient="0.8 0.8 0.8" />
  </visual>

  <default>
    <joint type="hinge" pos="0 0 0" axis="0 0 1" limited="true" range="0 120" damping="0.1"/>
    <muscle ctrllimited="true" ctrlrange="0 1"/>
  </default>

  <asset>
    <texture type="skybox" builtin="gradient" rgb1="0.6 0.6 0.6" rgb2="0 0 0" width="512" height="512"/>
    <texture name="texplane" type="2d" builtin="checker" rgb1=".25 .25 .25" rgb2=".3 .3 .3" width="512" height="512" mark="cross" markrgb=".8 .8 .8"/>
    <material name="matplane" reflectance="0.3" texture="texplane" texrepeat="1 1" texuniform="true"/>
  </asset>

  <worldbody>
    <geom name="floor" pos="0 0 -0.5" size="0 0 1" type="plane" material="matplane"/>

    <light directional="true" diffuse=".8 .8 .8" specular=".2 .2 .2" pos="0 0 5" dir="0 0 -1"/>

    <site name="s0" pos="-0.15 0 0" size="0.02"/>
    <site name="x0" pos="0 -0.15 0" size="0.02" rgba="0 .7 0 1" group="1"/>

    <body pos="0 0 0">
      <geom name="upper arm" type="capsule" size="0.045" fromto="0 0 0  0.5 0 0" rgba=".5 .1 .1 1"/>
      <joint name="shoulder"/>
      <geom name="shoulder" type="cylinder" pos="0 0 0" size=".1 .05" rgba=".5 .1 .8 .5" mass="0" group="1"/>

      <site name="s1" pos="0.15 0.06 0" size="0.02"/>
      <site name="s2" pos="0.15 -0.06 0" size="0.02"/>
      <site name="s3" pos="0.4 0.06 0" size="0.02"/>
      <site name="s4" pos="0.4 -0.06 0" size="0.02"/>
      <site name="s5" pos="0.25 0.1 0" size="0.02"/>
      <site name="s6" pos="0.25 -0.1 0" size="0.02"/>
      <site name="x1" pos="0.5 -0.15 0" size="0.02" rgba="0 .7 0 1" group="1"/>

      <body pos="0.5 0 0">
        <geom name="forearm" type="capsule" size="0.035" fromto="0 0 0  0.5 0 0" rgba=".5 .1 .1 1"/>
        <joint name="elbow"/>
        <geom name="elbow" type="cylinder" pos="0 0 0" size=".08 .05" rgba=".5 .1 .8 .5" mass="0" group="1"/>

        <site name="s7" pos="0.11 0.05 0" size="0.02"/>
        <site name="s8" pos="0.11 -0.05 0" size="0.02"/>
      </body>
    </body>
     <light name="light_animat" mode="trackcom" directional="false" castshadow="true" active="true" pos="-1 2.1741625722587483 2.2963050993692509" dir="1 -2.1741625722587483 -2.2963050993692509" attenuation="1 0 0" cutoff="45" exponent="1" ambient="1 1 1" diffuse="1.0 1.0 1.0" specular="0.29999999999999999 0.29999999999999999 0.29999999999999999"/>
  </worldbody>
  <tendon>
    <spatial name="SF" width="0.01">
      <site site="s0"/>
      <geom geom="shoulder"/>
      <site site="s1"/>
    </spatial>

    <spatial name="SE" width="0.01">
      <site site="s0"/>
      <geom geom="shoulder" sidesite="x0"/>
      <site site="s2"/>
    </spatial>

    <spatial name="EF" width="0.01">
      <site site="s3"/>
      <geom geom="elbow"/>
      <site site="s7"/>
    </spatial>

    <spatial name="EE" width="0.01">
      <site site="s4"/>
      <geom geom="elbow" sidesite="x1"/>
      <site site="s8"/>
    </spatial>

    <spatial name="BF" width="0.009" rgba=".4 .6 .4 1">
      <site site="s0"/>
      <geom geom="shoulder"/>
      <site site="s5"/>
      <geom geom="elbow"/>
      <site site="s7"/>
    </spatial>

    <spatial name="BE" width="0.009" rgba=".4 .6 .4 1">
      <site site="s0"/>
      <geom geom="shoulder" sidesite="x0"/>
      <site site="s6"/>
      <geom geom="elbow" sidesite="x1"/>
      <site site="s8"/>
    </spatial>
  </tendon>

  <actuator>
    <muscle name="SF" tendon="SF"/>
    <muscle name="SE" tendon="SE"/>
    <muscle name="EF" tendon="EF"/>
    <muscle name="EE" tendon="EE"/>
    <muscle name="BF" tendon="BF"/>
    <muscle name="BE" tendon="BE"/>
  </actuator>
</mujoco>"""
)

model = mujoco.MjModel.from_xml_path("/Users/tatarama/fork/mujoco/model/humanoid/humanoid.xml")
model = mujoco.MjModel.from_xml_path("/Users/tatarama/fork/mujoco_menagerie/unitree_a1/a1.xml")


# model = mujoco.MjModel.from_xml_path("/Users/tatarama/projects/work/research/neuromechanics/quadruped/mice/mouse-locomotion/src/scripts/scratch/siggraph/logs/sim_mjcf.xml")

data = mujoco.MjData(model)


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


class MujocoExtension(CustomExtension):
    """ MuJoCo """

    def __init__(self):
        self.show_window = False
        self.window_name = "MuJoCo"
        self._io = imgui.get_io()
        self.performance_warnings = []

        self.camera = mujoco.MjvCamera()
        self.option = mujoco.MjvOption()
        self.option.flags[mujoco.mjtVisFlag.mjVIS_LIGHT] = True
        model.vis.headlight.ambient[:] = [0.6]*3
        model.vis.headlight.diffuse[:] = [0.4]*3
        model.vis.headlight.specular[:] = [0.5]*3
        self.perturb = mujoco.MjvPerturb()
        mujoco.mjv_defaultCamera(self.camera)
        mujoco.mjv_defaultPerturb(self.perturb)
        mujoco.mjv_defaultOption(self.option)
        self.mj_context = mujoco.MjrContext(model, mujoco.mjtFontScale.mjFONTSCALE_150)
        self.scene = mujoco.MjvScene(model, maxgeom=1000000)

        self.viewport = mujoco.MjrRect(0, 0, 0, 0)
        self.width, self.height = 1280, 720
        self.max_width, self.max_height = 1920, 1080
        self.viewport.width, self.viewport.height = self.width, self.height
        self.framebuffer = None
        self.depth_buffer = None
        self.texture_id = None
        self.create_framebuffer(self.width, self.height)

        self.start_time = data.time

    def __del__(self):
        print("Terminating MuJoCo Extension")

    def get_name(self) -> str:
        return "MuJoCo"

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
        self.width = width
        self.height = height

        # Delete old OpenGL resources
        GL.glDeleteTextures([self.texture_id])
        GL.glDeleteRenderbuffers(1, [self.depth_buffer])
        GL.glDeleteFramebuffers(1, [self.framebuffer])

        # Recreate them with new size
        self.viewport.width, self.viewport.height = width, height

        self.create_framebuffer(self.width, self.height)

    def render_window(self) -> None:
        # self.scene.flags[0] = 0
        # self.scene.flags[2] = 0
        self.start_time = data.time
        while (data.time - self.start_time < 1.0/60.0):
            mujoco.mj_step(model, data)

        # Bind framebuffer
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.framebuffer)
        GL.glViewport(0, 0, self.width, self.height)

        # Minimal OpenGL setup - let MuJoCo handle lighting
        # GL.glEnable(GL.GL_DEPTH_TEST)
        # GL.glEnable(GL.GL_FRAMEBUFFER_SRGB)
        GL.glClearColor(0.1, 0.1, 0.1, 1.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)

        # Update and render
        mujoco.mjv_updateScene(model, data, self.option, None, self.camera,
                              mujoco.mjtCatBit.mjCAT_ALL, self.scene)
        mujoco.mjr_render(self.viewport, self.scene, self.mj_context)
        # GL.glDisable(GL.GL_FRAMEBUFFER_SRGB)
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)

        if imgui.is_window_hovered():
            self.mouse_iteractions()
            self.keyboard_interactions()

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
            int(self.texture_id),
            imgui.ImVec2((draw_width, draw_height)),
            uv0=imgui.ImVec2((1,1)),
            uv1=imgui.ImVec2((0,0)),
            # border_color=imgui.ImVec4((1, 0, 0, 1))
        )

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
                model,
                mujoco.mjtMouse.mjMOUSE_ROTATE_H,
                -mouse_delta.x / self.width,
                0.0,
                self.scene,
                self.camera,
            )
            mujoco.mjv_moveCamera(
                model,
                mujoco.mjtMouse.mjMOUSE_ROTATE_V,
                0.0,
                mouse_delta.y / self.height,
                self.scene,
                self.camera,
            )
        elif imgui.is_key_down(imgui.Key.mouse_right):
            mujoco.mjv_moveCamera(
                model,
                mujoco.mjtMouse.mjMOUSE_MOVE_H,
                -mouse_delta.x / self.width,
                0.0,
                self.scene,
                self.camera,
            )
            mujoco.mjv_moveCamera(
                model,
                mujoco.mjtMouse.mjMOUSE_MOVE_V,
                0.0,
                mouse_delta.y / self.height,
                self.scene,
                self.camera,
            )
        elif imgui.is_key_down(imgui.Key.mouse_wheel_y):
            mujoco.mjv_moveCamera(
                model,
                mujoco.mjtMouse.mjMOUSE_ZOOM,
                0.0,
                np.sign(mouse_wheel)*0.05*1,
                self.scene,
                self.camera,
            )
