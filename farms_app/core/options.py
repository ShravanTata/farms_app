from typing import Any, Dict, Iterable, List, Self, Type, Union

from farms_core.options import Options


class ApplicationOptions(Options):
    """ Application options """

    def __init__(self, **kwargs):
        "Initialize"
        super().__init__()

        # Main
        self.title = kwargs.pop("title", "FARMS")  # FARMS by default
        self.geometry: Iterable[int, int] = kwargs.pop("geometry", [720, 1080])
        self.resizable: bool = kwargs.pop("resizable", True)
        self.plugin_paths: List[str] = []        # Paths to search for the plugins
        self.backend: str = None

        # Imgui Ini options. Imgui uses ini files to save and restore the state of the
        # app and this can be used in conjunction to the FARMS options to either
        # override or save use preferences.

        # Window options

        # Docking options

        # Backends

        # FPS
        self.fps = kwargs.pop("fps", 60.0)       # 60 FPS by default

        # Plot options


class WindowOptions(Options):
    """ Window options """

    def __init__(self, **kwargs):
        super().__init__()
        self.vsync = kwargs.pop("vsync", True)
        self.fullscreen = kwargs.pop("fullscreen", False)


class DockingOptions(Options):
    """ Docking Options """

    def __init__(self, **kwargs):
        super().__init__()
        self.enabled = kwargs.pop("enabled", True)
        self.layout_config = kwargs.pop("layout_config", None)


class PluginOptions(Options):
    """Plugin Options """

    def __init__(self, **kwargs):
        super().__init__()
        self.auto_load = kwargs.pop("auto_load", True)
        self.enabled = kwargs.pop("enabled", [])
