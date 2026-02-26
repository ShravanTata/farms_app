import importlib

import os
import mujoco
import numpy as np
import OpenGL.GL as GL
from farms_app.core.extension import WorkflowExtension
from farms_app.core.window import BaseWindow
from farms_core import pylog
from farms_core.io import sdf
from farms_core.io.yaml import read_yaml
from farms_core.model.control import AnimatController, ControlType
from farms_core.model.data import AnimatData
from farms_core.model.options import (AnimatOptions, ArenaOptions,
                                      ControlOptions, JointOptions,
                                      LinkOptions, ModelOptions,
                                      MorphologyOptions, MotorOptions,
                                      MuscleOptions, SensorsOptions,
                                      SpawnLoader, SpawnOptions)
from farms_core.sensors import sensor_convention as sc
from farms_core.simulation.options import SimulationOptions, Simulator
from farms_sim.simulation import simulation_setup
from imgui_bundle import imgui, implot
from imgui_bundle import portable_file_dialogs as pfd
from dm_control.rl.control import PhysicsError
import traceback


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


class AnalysisWindow(BaseWindow):
    """ FARMS Analysis Window """

    def __init__(
            self,
            extension,
            sim,
            farms_data,
    ):
        name: str = "Analysis"
        super().__init__(name, extension)
        self.sim = sim
        self.farms_data = farms_data

    def on_initialize(self):
        """ Initialize """

    def on_render(self):
        """ On render """
        buffer_iteration = self.sim.task.iteration%self.sim.task.buffer_size
        self.draw_joint_positions(buffer_iteration, self.farms_data)

    def draw_joint_positions(self, iteration, farms_data):

        joint_names = farms_data.sensors.joints.names
        joints_data = farms_data.sensors.joints

        if iteration < 1000:
            plot_data = np.array(joints_data.positions_all()[:iteration, :])
        else:
            plot_data = np.array(joints_data.positions_all()[iteration-1000:iteration, :])
        times = np.array((np.linspace(0.0, 1.0, 1000)*-1.0)[::-1])

        if implot.begin_subplots("Joint Positions", 6, 2, imgui.ImVec2(-1, -1),):
            for index, name in enumerate(joint_names):
                if implot.begin_plot(f"{'-'.join(name.split('_')[:-2])}"):
                    implot.setup_axis(implot.ImAxis_.y1, "")
                    implot.setup_axis(
                        implot.ImAxis_.x1,
                        "", flags=(implot.AxisFlags_.no_tick_labels | implot.AxisFlags_.no_tick_marks)
                    )
                    implot.setup_axis_links(implot.ImAxis_.x1, implot.BoxedValue(-1.0), implot.BoxedValue(0.0))
                    implot.setup_axis_limits_constraints(implot.ImAxis_.x1, -1.0, 0.0)
                    implot.plot_line(
                        joint_names[index], times, np.rad2deg(np.ascontiguousarray(plot_data[:, index]))
                    )
                    implot.end_plot()
            implot.end_subplots()


class MuJoCoWindow(BaseWindow):
    """ MuJoCo Window """

    def __init__(
            self,
            extension,
            model,
            data,
            window_size: tuple = (1280, 720)
    ):
        name: str = "MuJoCo"
        super().__init__(name, extension)
        self._io = imgui.get_io()
        self.model = model
        self.data = data
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
        """ On initializing the window """

        # Setup mujoco scene
        self.setup_mj_scene()

        # Create framebuffer
        self.framebuffer, self.texture_id, self.depth_buffer = MuJoCoWindow.create_framebuffer(
            self.width, self.height
        )

    def _get_names_from_mjenum(self, mj_enum):
        return [
            name.split("_")[-1]
            for name in mj_enum.__members__.keys()
        ]

    def render_physics_controls(self):
        """ Render physics controls """
        # Integrator
        integrator_options = self._get_names_from_mjenum(mujoco.mjtIntegrator)
        changed, enum_id = imgui.combo(
            "Integrator", self.model.opt.integrator, integrator_options
        )
        if changed:
            self.model.opt.integrator = enum_id

        # Cone
        cone_options = self._get_names_from_mjenum(mujoco.mjtCone)
        changed, enum_id = imgui.combo("Cone", self.model.opt.cone, cone_options)
        if changed:
            self.model.opt.cone = enum_id

        # Jacobian
        jacobian_options = self._get_names_from_mjenum(mujoco.mjtJacobian)
        changed, enum_id = imgui.combo("Jacobian", self.model.opt.jacobian, jacobian_options)
        if changed:
            self.model.opt.jacobian = enum_id

        # Solver
        solver_options = self._get_names_from_mjenum(mujoco.mjtSolver)
        changed, enum_id = imgui.combo("Solver", self.model.opt.solver, solver_options)
        if changed:
            self.model.opt.solver = enum_id

    def _set_mjopt_param(self, name, mj_opt, opt_type, opt_range=None):
        if opt_type == "int":
            changed, val = imgui.input_int(name, self.model.opt.__getattribute__(mj_opt))
        elif opt_type == "float":
            changed, val = imgui.input_float(name, self.model.opt.__getattribute__(mj_opt))
        if changed:
            self.model.opt.__setattr__(
                mj_opt, min(opt_range[1], max(opt_range[0], val)) if opt_range else val
            )

    def render_algorithmic_params(self):
        """ Algorithm parameters """
        self._set_mjopt_param("Timestep", "timestep", "float", [0.0, 1.0])
        self._set_mjopt_param("Iterations", "iterations", "int", [0, 1000])
        self._set_mjopt_param("Tolerance", "tolerance", "float", [0.0, 1.0])
        self._set_mjopt_param("LS Iter", "ls_iterations", "int", [0, 100])
        self._set_mjopt_param("LS Tol", "ls_tolerance", "float", [0.0, 1.0])
        self._set_mjopt_param("Noslip Iter", "noslip_iterations", "int", [0, 1000])
        self._set_mjopt_param("Noslip Tol", "noslip_tolerance", "float", [0.0, 1.0])
        self._set_mjopt_param("API Rate", "apirate", "float", [0.0, 1000.0])
        self._set_mjopt_param("SDF Iter", "sdf_iterations", "int", [1, 20])
        self._set_mjopt_param("SDF Init", "sdf_initpoints", "int", [1, 100])

    def render_left_controls(self):
        """ Render controls """
        # --- Physics Section ---
        if imgui.collapsing_header("Physics"):
            self.render_physics_controls()

        # --- Algorithmic Parameters ---
        if imgui.collapsing_header("Algorithmic Parameters"):
            self.render_algorithmic_params()

        if imgui.collapsing_header("Autogenerated"):
            for opt in dir(self.model.opt):
                if "__" not in opt:
                    imgui.button(opt)

    def render_right_controls(self):
        """ Render controls """
        imgui.button("Button 3")

    def render_main_scene(self):
        """ Render main scene """
        # Bind framebuffer
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.framebuffer)
        GL.glViewport(0, 0, self.width, self.height)

        # Minimal OpenGL setup - let MuJoCo handle lighting
        # GL.glEnable(GL.GL_DEPTH_TEST)
        # GL.glEnable(GL.GL_FRAMEBUFFER_SRGB)
        GL.glClearColor(0.1, 0.1, 0.1, 1.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)

        # Update and render
        mujoco.mjv_updateScene(
            self.model, self.data, self.mj_option, None, self.mj_camera,
            mujoco.mjtCatBit.mjCAT_ALL, self.mj_scene
        )
        mujoco.mjr_render(self.mj_viewport, self.mj_scene, self.mj_context)
        try:
            # Exception handling necessary for Nvidia + Wayland
            GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
        except GL.GLError:
            pass
        # GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
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

        imgui.image(
            # "##",
            imgui.ImTextureRef(self.texture_id),
            # self.texture_id,
            imgui.ImVec2((self.width, self.height)),
            uv0=imgui.ImVec2((1, 1)),
            uv1=imgui.ImVec2((0, 0)),
        )
        if imgui.is_item_hovered():
            self.is_scene_hovered = True
        else:
            self.is_scene_hovered = False

    def on_render(self):
        """ Render window """
        imgui.begin_child("##LeftPanel", size=(200, 0), child_flags=imgui.ChildFlags_.borders | imgui.ChildFlags_.resize_x)
        self.render_left_controls()
        imgui.end_child()

        imgui.same_line()

        imgui.begin_child("##Viewer", size=(self.width*0.75, self.height*0.75), child_flags=imgui.ChildFlags_.borders)
        self.render_main_scene()
        imgui.end_child()

        imgui.same_line()

        imgui.begin_child("##RightPanel", child_flags=imgui.ChildFlags_.borders | imgui.ChildFlags_.resize_x)
        self.render_right_controls()
        imgui.end_child()

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
        self.mj_scene = mujoco.MjvScene(self.model, maxgeom=1000000)

        self.mj_viewport = mujoco.MjrRect(0, 0, 0, 0)
        self.mj_viewport.width, self.mj_viewport.height = self.width, self.height

    @staticmethod
    def create_framebuffer(width: int, height: int):
        """ Create Framebuffer """
        texture_id = GL.glGenTextures(1)

        GL.glBindTexture(GL.GL_TEXTURE_2D, texture_id)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA, width, height, 0,
                        GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, None)
        # Set texture parameters
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)

        # Create framebuffer
        framebuffer = GL.glGenFramebuffers(1)
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, framebuffer)

        # Attach texture to framebuffer
        GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER, GL.GL_COLOR_ATTACHMENT0,
                                  GL.GL_TEXTURE_2D, texture_id, 0)

        # Create depth buffer
        depth_buffer = GL.glGenRenderbuffers(1)
        GL.glBindRenderbuffer(GL.GL_RENDERBUFFER, depth_buffer)
        GL.glRenderbufferStorage(
            GL.GL_RENDERBUFFER, GL.GL_DEPTH_COMPONENT24, width, height
        )
        GL.glFramebufferRenderbuffer(GL.GL_FRAMEBUFFER, GL.GL_DEPTH_ATTACHMENT,
                                    GL.GL_RENDERBUFFER, depth_buffer)

        # Check framebuffer completeness
        if GL.glCheckFramebufferStatus(GL.GL_FRAMEBUFFER) != GL.GL_FRAMEBUFFER_COMPLETE:
            pylog.error("Framebuffer not complete!")

        # GL.glEnable(GL.GL_MULTISAMPLE)

        # unbind framebuffer
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
        return framebuffer, texture_id, depth_buffer

    def resize_framebuffer(self, width, height):
        # Delete old OpenGL resources
        GL.glDeleteTextures([self.texture_id])
        GL.glDeleteRenderbuffers(1, [self.depth_buffer])
        GL.glDeleteFramebuffers(1, [self.framebuffer])

        # Recreate them with new size
        self.mj_viewport.width, self.mj_viewport.height = width, height

        self.framebuffer, self.texture_id, self.depth_buffer = MuJoCoWindow.create_framebuffer(
            self.width, self.height
        )

    def run_simulation(self):
        """ Run Simulation """
        self.start_time = self.data.time
        while (self.data.time - self.start_time < 1.0/60.0):
            mujoco.mj_step(self.model, self.data)

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


class FarmsSimulatorExtension(WorkflowExtension):
    """ FARMS Simulation """

    def __init__(self):
        self.hide = False
        super().__init__(name="FARMS")
        self._io = imgui.get_io()
        self.sim = None
        self.dt_remainder = 0.0
        self.playback_speed = 0.1

        # FARMS
        self.exp_options = None
        self.simulation_options = None
        self.arena_options = None
        self.animat_options = None

    def register_windows(self):
        """ Register windows """
        self.register_window(MuJoCoWindow(self, self.model, self.data))
        self.register_window(AnalysisWindow(self, self.sim, self.farms_data))

    def setup_simulation(self):
        self.animat_data = AnimatData.from_options(
            animat_options=self.animat_options,
            simulation_options=self.simulation_options,
        )

        # Controller
        self.animat_controller = TestController(
            joint_names=(
                [
                    joint['joint_name']
                    for joint in self.animat_options['control']['motors']
                    if ControlType.to_string(ControlType.POSITION) in joint['control_types']
                ],
                [],
                [
                    joint['joint_name']
                    for joint in self.animat_options['control']['motors']
                    if ControlType.to_string(ControlType.TORQUE) in joint['control_types']
                ],
                [],
                [],
            ),
            muscles_names=[
                muscle.name.lower()
                for muscle in self.animat_options.control.hill_muscles
            ],
            max_torques=(
                [],
                [],
                self.animat_options.control.motors_limits_torque(),
                [],
                []
            ),
        )

        # Simulation
        self.sim = simulation_setup(
            animat_options=self.animat_options,
            simulation_options=self.simulation_options,
            arena_options=self.arena_options,
            animat_data=self.animat_data,
            animat_controller=self.animat_controller,
            simulator=Simulator.MUJOCO,
        )

        self.model = self.sim.physics.model._model
        self.data = self.sim.physics.data._data

        # data: FARMS data for physics simulations
        self.farms_data = self.sim.task.data

    def cleanup(self):
        """ Cleanup  """
        pass

    def get_dependencies(self):
        return []

    def render_menu(self):
        """ Render menu """
        imgui.begin_menu_bar()
        if imgui.begin_menu("File"):
            if imgui.menu_item_simple("Open"):
                try:
                    self.load_experiment()
                except Exception as e:
                    pylog.error("Unable to load the model")
            if imgui.menu_item_simple("Reload"):
                pass
            if imgui.menu_item_simple("Close"):
                pass
            imgui.end_menu()
        if imgui.begin_menu("Simulation"):
            if imgui.menu_item_simple("Experiment"):
                pass
            imgui.end_menu()
        if imgui.begin_menu("Window"):
            for window in self.windows:
                if imgui.menu_item_simple(window.name, selected=window.visible):
                    window.visible = not window.visible
            imgui.end_menu()
        imgui.end_menu_bar()

    def on_update(self):
        # Normal GUI operation
        if self.sim:
            dt = 1/60
            self.n_steps = int(1000 * (dt + self.dt_remainder) * self.playback_speed)
            self.dt_remainder = (1000 * (dt + self.dt_remainder) * self.playback_speed - self.n_steps) / 1000

            self.n_steps = max(0, self.n_steps)  # Ensure non-negative

            # Update GUI states

            for ii in range(self.n_steps):
                try:
                    if self.sim.task.iteration == (self.sim.task.n_iterations):
                        self.sim._env._step_count = 0
                        self.sim.task.iteration = 0
                        self.sim.task.sim_iteration = 0
                        self.sim._env._reset_next_step = False
                    self.sim._env.step(action=None)
                except PhysicsError as err:
                    pylog.error(traceback.format_exc())
                    if self.sim.handle_exceptions:
                        return
                    raise err

    def import_mod(self, name):
        mod, _, attr = name.rpartition('.')
        return getattr(importlib.import_module(mod), attr)

    def init_farms_loaders(self, loaders: dict):
        """ Init loaders """
        self.sim_opts_loader = self.import_mod(loaders['simulation_options'])
        self.animats_opts_loader = self.import_mod(loaders['animats_options'][0])
        self.arenas_opts_loader = self.import_mod(loaders['arenas_options'][0])
        self.animats_data_loader = self.import_mod(loaders['animats_data'][0])

    def load_experiment(self):
        """ Load experiment """
        self.result = pfd.open_file(
            "Experiment options",
            default_path="",
            filters=("*.yaml",)
        ).result()
        os.chdir(os.path.dirname(self.result[0]))
        self.exp_options = read_yaml(self.result[0])
        # loaders
        self.init_farms_loaders(self.exp_options['loaders'])
        # Load from options
        animat_config = read_yaml(self.exp_options['animats'][0])
        self.animat_options = self.animats_opts_loader(
            sdf=animat_config['sdf'],
            spawn=animat_config['spawn'],
            morphology=animat_config['morphology'],
            control=animat_config['control'],
        )
        self.animat_options['mujoco'] = animat_config['mujoco']
        self.animat_options['name'] = animat_config['name']
        arena_config = read_yaml(self.exp_options['arenas'][0])
        self.arena_options = self.arenas_opts_loader(
            sdf=arena_config['sdf'],
            spawn=arena_config['spawn'],
            water=arena_config['water'],
            ground_height=arena_config['ground_height'],
        )
        sim_config = read_yaml(self.exp_options['simulation'])
        self.simulation_options = self.sim_opts_loader(**sim_config)

    def on_render(self):
        """ On render """
        if self.exp_options and self.animat_options and self.arena_options and self.simulation_options:
            self.setup_simulation()
            self.register_windows()
            self.windows[1].initialize()
            self.exp_options = None

    def on_event(self):
        """ On events """
        if len(self.windows) > 1:
            if self.windows[1].is_scene_hovered:
                self.windows[1].mouse_iteractions()
                self.windows[1].keyboard_interactions()


class TestController(AnimatController):
    """ Animat controller """

    def __init__(
            self, joint_names, muscles_names, max_torques, **kwargs,
    ):
        super().__init__(joint_names, muscles_names, max_torques)

    def feedback(self, iteration, time, timestep):
        """ Update feedback """

    def step(self, iteration, time, timestep):
        """ Step your controller """
        pass

    def positions(self, iteration, time, timestep):
        """ Position control commands """
        return {
            joint: np.pi/4
            for joint in self.joints_names[ControlType.POSITION]
        }

    def excitations(self, iteration, time, timestep):
        """ Muscle control excitations """
        return np.array([
            0.0
            for index, muscle in enumerate(self.muscles_names)
        ])

    def torques(
            self,
            iteration: int,
            time: float,
            timestep: float,
    ):
        """Torques"""
        assert iteration >= 0
        assert time >= 0
        assert timestep > 0
        return {
            joint: 0
            for joint in self.joints_names[ControlType.TORQUE]
        }
