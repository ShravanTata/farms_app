from farms_app.plugins.base import BasePlugin
from farms_core import pylog
from farms_core.io.yaml import read_yaml
from imgui_bundle import imgui, implot

from farms_core.utils.profile import profile
from farms_core.simulation.options import Simulator
from farms_core.model.control import AnimatController
from farms_mujoco.simulation.simulation import Simulation as MuJoCoSimulation
from farms_mujoco.sensors.camera import CameraCallback, save_video
from farms_sim.utils.parse_args import sim_parse_args
from farms_sim.simulation import (
    setup_from_clargs,
    run_simulation,
    postprocessing_from_clargs,
)

from farms_amphibious.control.amphibious import get_amphibious_controller
from farms_amphibious.callbacks import setup_callbacks
from farms_amphibious.control.network import NetworkODE
from farms_amphibious.model.options import (
    AmphibiousOptions,
    AmphibiousArenaOptions,
)
from farms_amphibious.data.data import (
    AmphibiousData,
    AmphibiousExperimentData,
    get_amphibious_experiment_data,
)


class FarmsAmphibotPlugin(BasePlugin):
    """ FARMS Amphibot simulation """


    def __init__(self):
        self.show_window = True
        self.window_name = "Amphibot"
        self._io = imgui.get_io()
        self.sim = None

    def setup_simulation(self):
        """ Simulation setup """
