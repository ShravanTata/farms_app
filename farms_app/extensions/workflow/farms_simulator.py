from farms_app.core.extension import WorkflowExtension
from farms_app.core.window import BaseWindow
from farms_core import pylog
from farms_core.io.yaml import read_yaml
from imgui_bundle import imgui, implot
from imgui_bundle import portable_file_dialogs as pfd


from deap import base, creator
from dm_control.rl.control import PhysicsError
from farms_core.model.data import AnimatData
from farms_core.simulation.options import Simulator
from farms_muscle import rigid_tendon
from abstract_control.application.options import get_mouse_options
from farms_sim.simulation import simulation_setup
from abstract_control import callbacks
from abstract_control.control.generate import quadruped_siggraph_network
from abstract_control.control.neural_control import NeuralController
import mujoco
import numpy as np
import OpenGL.GL as GL
from farms_core import pylog
from farms_core.io import sdf
from farms_core.io.yaml import read_yaml
from farms_core.model.control import AnimatController, ControlType
from farms_core.model.options import (AnimatOptions, ArenaOptions,
                                      ControlOptions, JointOptions,
                                      LinkOptions, ModelOptions,
                                      MorphologyOptions, MotorOptions,
                                      MuscleOptions, SensorsOptions,
                                      SpawnLoader, SpawnOptions)
from farms_network.core.network import Network
from farms_network.core.options import NetworkOptions
from farms_core.sensors import sensor_convention as sc
from farms_core.simulation.options import SimulationOptions, Simulator
import farms_app.extensions.workflow.network as generate
import traceback
import networkx as nx


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

        imgui.image_button(
            "##",
            self.texture_id, # imgui.ImTextureRef(self.texture_id)
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


class NetworkVisualizerWindow(BaseWindow):

    def __init__(self, extension, network: Network = None):
        name: str = "network-viz"
        super().__init__(name, extension)
        if network is not None:
            self.network = network
        else:
            network_options = NetworkOptions.from_options(
                read_yaml("/tmp/network_options.yaml")
            )

            self.network = Network.from_options(network_options)

    def on_initialize(self):
        """ On initialize """
        edges_xy = np.array(
            [
                self.network.options.nodes[node_idx].visual['position'][:2]
                for edge in self.network.options.edges
                for node_idx in (
                        self.network.options.nodes.index(edge.source),
                        self.network.options.nodes.index(edge.target),
                )
            ]
        )
        self.edges_x = np.array(edges_xy[:, 0])
        self.edges_y = np.array(edges_xy[:, 1])

    def on_update(self):
        """ On update of the application """

    def on_render(self):
        """ Render main extension dockspace """
        imgui.text("Inside a dock host")
        self.draw_network()

    def draw_network(self):
      nodes = self.network.options.nodes
      edges = self.network.options.edges

      imgui.WindowFlags_
      flags = (
          implot.AxisFlags_.no_label |
          implot.AxisFlags_.no_tick_labels |
          implot.AxisFlags_.no_tick_marks
      )
      if implot.begin_plot("vis", size=(-1, -1), flags=implot.Flags_.equal):
          implot.setup_axis(implot.ImAxis_.x1, flags=flags)
          implot.setup_axis(implot.ImAxis_.y1, flags=flags)
          implot.plot_line(
              "",
              xs=self.edges_x,
              ys=self.edges_y,
              flags=implot.LineFlags_.segments
          )
          radius = 0.1
          circ_x = radius*np.cos(np.linspace(-np.pi, np.pi, 50))
          circ_y = radius*np.sin(np.linspace(-np.pi, np.pi, 50))
          for index, node in enumerate(nodes):
              implot.set_next_marker_style(
                  size=10.0 # *node.vi3sual.radius
              )
              implot.push_style_var(implot.StyleVar_.fill_alpha, 1.0)
              implot.plot_scatter(
                  "##",
                  xs=np.array((node.visual['position'][0],)),
                  ys=np.array((node.visual['position'][1],)),
              )
              implot.pop_style_var()
              implot.plot_text(
                  node.visual['label'].replace("\\textsubscript", "")[0],
                  node.visual['position'][0],
                  node.visual['position'][1],
              )
          implot.end_plot()


class FarmsSimulatorExtension(WorkflowExtension):
    """ FARMS Simulation """


    def __init__(self):
        self.hide = False
        super().__init__(name="FARMS")
        self._io = imgui.get_io()
        self.sim = None
        self.dt_remainder = 0.0
        self.playback_speed = 0.1
        self.sim_options = None
        self.arena_options = None
        self.animat_options = None
        self.optimization_parameters = None
        n_vars = 286
        n_samples = 30
        self.optimization_parameters = np.random.normal(
            loc=-1.0, scale=1.0, size=(n_samples, n_vars)
        )

        # self.setup_simulation()
        # self.register_window(MuJoCoWindow(self, self.model, self.data))
        self.register_window(NetworkVisualizerWindow(self))

    def setup_simulation(self):

        self.sim_options, self.arena_options, self.animat_options = get_mouse_options(
            gui=True, show_progress=False, iterations=1000000,
            terrain="flat", randomize_spawn=False
        )

        options = {
            "callbacks": [],
            "handle_exceptions": True
        }

        pelvis_body_support_options = {
            'body_support_link': 'THORACIC13',
            'spring_constants': np.array(
                [1e3, 1e3*0.0, 1e3, 1e-1, 1e-1, 1e-1]
            ),
            'damping_constants': np.array(
                [1e2, 1e2*0.0, 1e2, 1e-3, 1e-3, 1e-3]
            ),
            'desired_linpos': np.array(self.animat_options.spawn.pose[:3]),
            'desired_angpos': np.array(self.animat_options.spawn.pose[3:]),
            'desired_linvel': np.zeros((3,)),
            'desired_angvel': np.zeros((3,)),
            'fading_flags': np.zeros((6,)),
            'fading_time': 5.0*1e3,
        }

        head_body_support_options = {
            'body_support_link': 'HEAD',
            'spring_constants': np.array([1e1, 0.0, 5e1, 0.0, 0.0, 0.0])*1e1,
            'damping_constants': np.array([1e0, 0.0, 5e0, 0.0, 0.0, 0.0])*1e1,
            'desired_linpos': np.array(self.animat_options.spawn.pose[:3]),
            'desired_angpos': np.zeros((3,)),
            'desired_linvel': np.zeros((3,)),
            'desired_angvel': np.zeros((3,)),
            'fading_flags': np.zeros((6,)),
            'fading_time': 3.5*1e3,
        }

        options['callbacks'].append(
            callbacks.BodySupport(
                **pelvis_body_support_options
            )
        )

        self.animat_data = AnimatData.from_options(
            animat_options=self.animat_options,
            simulation_options=self.sim_options,
        )

        # Optimization torques
        options['callbacks'].append(callbacks.OptimizationData(n_iterations=self.sim_options.n_iterations))

        # Controller
        network_graph = quadruped_siggraph_network()
        self.animat_controller = NeuralController(
            (
                [],
                [],
                [
                    joint.name
                    for joint in self.animat_options.morphology.joints
                    if ("HIND" not in joint.name) and ("FORE" not in joint.name) and ("support" not in joint.name)
                ],
                [
                    joint.name
                    for joint in self.animat_options.morphology.joints
                    if ("HIND" not in joint.name) and ("FORE" not in joint.name) and ("support" not in joint.name)
                ],
                [],
            ),
            [
                muscle.name
                for muscle in self.animat_options.control.hill_muscles
            ],
            ([], [], [], [], []),
            springrefs={
                joint.name: joint.springref
                for joint in self.animat_options.morphology.joints
            },
            n_iterations=self.sim_options.buffer_size,
            animat_data=self.animat_data,
            network_graph=network_graph,
            opt_parameters=self.optimization_parameters[0],
            units=self.sim_options.units,
            total_mass=self.animat_options.total_mass,
        )
        # Simulation
        self.sim = simulation_setup(
            animat_options=self.animat_options,
            simulation_options=self.sim_options,
            arena_options=self.arena_options,
            animat_data=self.animat_data,
            animat_controller=self.animat_controller,
            simulator=Simulator.MUJOCO,
            **options,
        )

        self.model = self.sim.physics.model._model
        self.data = self.sim.physics.data._data
        self.camera = mujoco.MjvCamera()
        self.option = mujoco.MjvOption()
        self.mj_context = mujoco.MjrContext(
            self.model, mujoco.mjtFontScale.mjFONTSCALE_150
        )
        self.scene = mujoco.MjvScene(self.model, maxgeom=10000)
        self.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW] = 0
        self.scene.flags[mujoco.mjtRndFlag.mjRND_REFLECTION] = 0
        self.model.vis.headlight.ambient = [0.5, 0.5, 0.5]
        self.perturb = mujoco.MjvPerturb()
        # Simulation data objects
        self.mj_data = self.sim.physics.data
        # data: FARMS data for physics simulations
        self.farms_data = self.sim.task.data
        # container: NETWORK data for the neural network
        self.container = self.sim.task._controller.container
        self._neural_outputs = self.container.neural.outputs.data_table

        self.neural_system = self.sim.task._controller.net_

        # FRAMEBUFFER
        self.mj_viewport = mujoco.MjrRect(0, 0, 0, 0)
        self.width, self.height = 720, 480
        self.max_width, self.max_height = 1920, 1080
        self.mj_viewport.width, self.mj_viewport.height = self.width, self.height
        self.framebuffer = None
        self.depth_buffer = None
        self.texture_id = None
        self.create_framebuffer(self.width, self.height)

        # Network
        self.graph = self.animat_controller.net_.graph
        self.edges_xy = np.array(
            [
                (node["x"], node["y"])
                for name, node in self.graph.nodes.items()
            ]
        )
        self.edges_x = np.array(self.edges_xy[:, 0])
        self.edges_y = np.array(self.edges_xy[:, 1])

        self.sparse_array = nx.to_scipy_sparse_array(self.graph)

    def cleanup(self):
        """ Cleanup  """
        pass

    def get_dependencies(self):
        return []

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

    def render_mujoco(self):
        # Bind framebuffer
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.framebuffer)
        GL.glViewport(0, 0, self.width, self.height)

        # Minimal OpenGL setup - let MuJoCo handle lighting
        # GL.glEnable(GL.GL_DEPTH_TEST)
        # GL.glEnable(GL.GL_FRAMEBUFFER_SRGB)
        GL.glClearColor(0.1, 0.1, 0.1, 1.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)

        # Update and render
        mujoco.mjv_updateScene(self.model, self.data, self.option, None, self.camera,
                              mujoco.mjtCatBit.mjCAT_ALL, self.scene)
        mujoco.mjr_render(self.mj_viewport, self.scene, self.mj_context)
        # GL.glDisable(GL.GL_FRAMEBUFFER_SRGB)
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)

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
        )

        if imgui.is_item_hovered():
            self.mouse_iteractions()
            self.keyboard_interactions()

    def draw_network(self, iteration):
        """ Draw network """

        nodes = self.graph.nodes

        imgui.WindowFlags_
        flags = (
            implot.AxisFlags_.no_label |
            implot.AxisFlags_.no_tick_labels |
            implot.AxisFlags_.no_tick_marks
        )
        if implot.begin_plot("vis", flags=implot.Flags_.equal):
            implot.setup_axis(implot.ImAxis_.x1, flags=flags)
            implot.setup_axis(implot.ImAxis_.y1, flags=flags)
            implot.plot_line(
                "",
                xs=self.edges_x,
                ys=self.edges_y,
                flags=implot.LineFlags_.segments
            )
            radius = 0.1
            circ_x = radius*np.cos(np.linspace(-np.pi, np.pi, 50))
            circ_y = radius*np.sin(np.linspace(-np.pi, np.pi, 50))
            for index, pos in enumerate(self.edges_xy):
                implot.set_next_marker_style(
                    size=10.0 # *node.vi3sual.radius
                )
                implot.push_style_var(implot.StyleVar_.fill_alpha, 0.5)
                implot.push_style_var(
                    implot.StyleVar_.fill_alpha,
                    0.05+self._neural_outputs[iteration, index]*3.0
                )
                implot.plot_scatter(
                    "##",
                    xs=np.array((pos[0],)),
                    ys=np.array((pos[1],)),
                )
                implot.pop_style_var()
                # implot.plot_text(
                #     ,
                #     node.visual.position[0],
                #     node.visual.position[1],
                # )

            implot.end_plot()

    def draw_connectivity_map(self):
        """ Draw connectivity """
        axes_flags = implot.AxisFlags_.lock | implot.AxisFlags_.no_grid_lines | implot.AxisFlags_.no_tick_marks
        implot.push_colormap(implot.Colormap_.viridis)
        if implot.begin_plot("Connectivity", flags=implot.Flags_.no_legend | implot.Flags_.no_mouse_text):
            implot.setup_axes("", "", axes_flags, axes_flags)
            implot.setup_axis_ticks(implot.ImAxis_.x1, values=[j for j in range(10)], labels=[f"{j}" for j in range(10)], keep_default=False)
            implot.setup_axis_ticks(implot.ImAxis_.y1, values=[j for j in range(10)], labels=[f"{j}" for j in range(10)], keep_default=False)
            implot.plot_heatmap(
                "network", self.sparse_array.todense(), label_fmt="%i"
            )
            implot.end_plot()
        implot.pop_colormap()

    def reset_simulation(self):
        """ Reset full simulation """
        self.sim._env._step_count = 0
        self.sim.task.iteration = 0
        self.sim.task.sim_iteration = 0
        self.sim._env._reset_next_step = True

    def on_update(self):
        # Normal GUI operation
        return
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

    def on_event(self):
        """ On events """
        # if self.windows[1].is_scene_hovered:
        #     self.windows[1].mouse_iteractions()
        #     self.windows[1].keyboard_interactions()

    def render_window(self) -> None:
        if not(self.animat_options and self.simulation_options and self.arena_options):
            if imgui.button("Load Animat"):
                self.result = pfd.open_file("Animat options", default_path="", filters=("*.yaml",)).result()
                self.animat_options = self.result[0]
            if imgui.button("Load Sim"):
                self.result = pfd.open_file("Sim options", default_path="", filters=("*.yaml",)).result()
                self.simulation_options = self.result[0]
            if imgui.button("Load Arena"):
                self.result = pfd.open_file("Arena options", default_path="", filters=("*.yaml",)).result()
                self.arena_options = self.result[0]
        else:
            self.setup_simulation()
            self.animat_options = None
            self.simulation_options = None
            self.arena_options = None

        if self.sim:
            self.update()
            self.render_mujoco()
            iteration = self.sim.task._controller.i_steps%1000
            self.draw_network(iteration)
            imgui.same_line()
            self.draw_connectivity_map()

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



def validate_network(network):
    """ Check that the network is consistent for simulation with farms_network """

    for from_node, to_node in network.edges():
        assert network.nodes[from_node], f"{from_node} neuron not defined!"
        assert network.nodes[to_node], f"{to_node} neuron not defined!"


class DummyController(AnimatController):
    """Dummy controller"""

    def __init__(
        self,
        joint_names,
        muscles_names,
        max_torques,
        **kwargs,
    ):
        super().__init__(joint_names, muscles_names, max_torques)
        self.springrefs_pos = kwargs.pop("springrefs")
        self.n_iterations = kwargs.pop("n_iterations", 1000)
        self.container = Container(max_iterations=self.n_iterations)
        network_graph = generate.simple_v3_motoneurons_network()
        # Validate network
        validate_network(network_graph)
        self.net_ = NeuralSystem(network_graph, container=self.container)
        self.container.initialize()
        self.net_.setup_integrator()
        self.animat_data = kwargs.pop("animat_data")

        self.u = np.zeros(np.shape(self.container.neural.inputs.values))
        self.u[
            [
                "alpha" in param.name
                for param in self.container.neural.inputs
            ]
        ] = 0.0
        self.container.neural.inputs.values = self.u
        self._time = 0.0
        self.network_output_indices = None
        self.__initialize_network_output_maps()
        self.network_input_indices = None
        self.num_network_inputs = len(self.container.neural.inputs.values)
        self.__initialize_network_input_maps()
        self.i_steps = 0

        contacts_data_idx = {
            contact_pair[0]: index
            for index, contact_pair in enumerate(self.animat_data.sensors.contacts.names)
        }

        self.animat_contact_indices = [
            contacts_data_idx[f"{side}_{name}"]
            for name in ("HIND_PHALANGE",)
            for side in ("RIGHT",)
        ]
        self.position_controls = {joint: 0.0 for joint in joint_names[0]}

    @classmethod
    def from_options(cls, animat_options, sim_options, animat_data):
        """Controller from animat options"""
        joint_names = (
            [
                joint['joint_name']
                for joint in animat_options['control']['motors']
                if ControlType.to_string(ControlType.POSITION) in joint['control_types']
            ],
            [
                joint['joint_name']
                for joint in animat_options['control']['motors']
                if ControlType.to_string(ControlType.VELOCITY) in joint['control_types']
            ],
            [
                joint['joint_name']
                for joint in animat_options['control']['motors']
                if ControlType.to_string(ControlType.TORQUE) in joint['control_types']
            ],
            [
                joint['joint_name']
                for joint in animat_options['control']['motors']
                if ControlType.to_string(ControlType.SPRINGREF) in joint['control_types']
            ],
            [],
        )
        muscles_names = [
            muscle.name.lower() for muscle in animat_options.control.hill_muscles
        ]
        max_torques = ([], [], [], [], [])
        springrefs = {
            joint.name: joint.springref for joint in animat_options.morphology.joints
        }
        n_iterations = sim_options.n_iterations
        animat_data = animat_data

        return cls(
            joint_names=joint_names,
            muscles_names=muscles_names,
            max_torques=max_torques,
            animat_data=animat_data,
            springrefs=springrefs,
            n_iterations=n_iterations,
        )

    def __initialize_network_output_maps(self):
        """Initialize output maps"""
        outputs = self.container.neural.outputs
        # feedbacks
        self.network_output_indices = {}
        self.network_output_indices["motorneurons"] = [
            outputs.name_index[f"nout_{name}_Mn"] for name in self.muscles_names
        ]

    def __initialize_network_input_maps(self):
        """Initialize input maps"""
        inputs = self.container.neural.inputs
        # feedbacks
        self.network_input_indices = {}

        # Feedbacks: Proprioceptive
        self.network_input_indices = {
            feedback: [
                inputs.name_index[f"aff_{name}_{feedback}"]
                for name in self.muscles_names
                if f"aff_{name}_{feedback}" in inputs.name_index
            ]
            for feedback in ("Ia", "II", "Ib",)
        }

        # Cutaneous
        self.network_input_indices["cut"] = [
            inputs.name_index[f"aff_{side}_{name}_cut"]
            for name in ("hind_PHALANGE", "fore_PHALANGE",)
            for side in ("left", "right")
            if f"aff_{side}_{name}_cut" in inputs.name_index
        ]

    def update_network_inputs(self, iteration, time, timestep):
        """Update feedbacks"""
        muscle_sensors = self.animat_data.sensors.muscles
        contact_sensors = self.animat_data.sensors.contacts
        link_sensors = self.animat_data.sensors.links

        network_inputs = self.container.neural.inputs

        _inputs = np.array(network_inputs.values)

        # feedbacks
        if self.network_input_indices["Ia"]:
            _inputs[self.network_input_indices["Ia"]] = np.array(
                muscle_sensors.Ia_feedbacks(iteration)
            )
        if self.network_input_indices["II"]:
            _inputs[self.network_input_indices["II"]] = np.array(
                muscle_sensors.II_feedbacks(iteration)
            )
        if self.network_input_indices["Ib"]:
            _inputs[self.network_input_indices["Ib"]] = np.array(
                muscle_sensors.Ib_feedbacks(iteration)
            )
        # somatosensory
        cutaneous = np.array(contact_sensors.reactions()[iteration, :, -1])[self.animat_contact_indices]

        if self.network_input_indices["cut"]:
            _inputs[self.network_input_indices["cut"]] = cutaneous/self.units.newtons
        network_inputs.values = _inputs

    def step(self, iteration, time, timestep):
        self.container.update_log()
        self.update_network_inputs(iteration, time, timestep)
        self.net_.step(dt=1)
        self._time += 1e-3
        self.i_steps += 1

    def positions(self, iteration, time, timestep):
        """ Position control commands """
        return {
            joint: self.position_controls[joint]
            for joint in self.joints_names[ControlType.POSITION]
        }

    def excitations(self, iteration, time, timestep):
        """Muscle control excitations"""
        neural_outputs = self.container.neural.outputs
        # if self._time < 0.1:
        #     return (
        #         np.array(neural_outputs.values)[
        #             self.network_output_indices["motorneurons"]
        #         ]
        #     )
        # else:
        return np.fmin(
                np.array(neural_outputs.values)[
                    self.network_output_indices["motorneurons"]
                ],
                1.0,
            )
        # return np.array(
        #     [np.sin(2 * np.pi * 0.5 * self._time) for muscle in self.muscles_names]
        # )

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
        return {joint: 0 for joint in self.joints_names[ControlType.TORQUE]}

    def springrefs(
        self,
        iteration: int,
        time: float,
        timestep: float,
    ):
        """Spring references"""
        assert iteration >= 0
        assert time >= 0
        assert timestep > 0
        return {name: value for name, value in self.springrefs_pos.items()}
