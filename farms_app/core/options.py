""" Options for FARMS Application """

from enum import StrEnum
from typing import Any, Dict, Iterable, List, Self, Type, Union

from farms_app.backends.manager import PlatformType, RendererType
from farms_core.options import Options


class PlatformType(StrEnum):
    """ Type of Platform """
    GLFW = 'glfw'


class RendererType(StrEnum):
    """ Type of Renderer """
    OPENGL2 = 'gl2'
    OPENGL3 = 'gl3'


class BackendOptions(Options):
    """ Backend renderer options """

    def __init__(self):
        super().__init__()
        self.platform = PlatformType.GLFW.value
        self.renderer = RendererType.OPENGL2.value


class PlatformOptions(Options):
    """ Base class for different types of platform options """

    def __init__(self):
        ...


class LaunchOptions(Options):
    """ Setup options to configure the interface at launch  """

    def __init__(self, **kwargs):
        self.title = kwargs.pop("title", "FARMS")  # FARMS by default
        self.geometry: Iterable[int, int] = kwargs.pop("geometry", [720, 1080])
        self.resizable: bool = kwargs.pop("resizable", True)


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


class ExtensionOptions(Options):
    """Extension Options """

    def __init__(self, **kwargs):
        super().__init__()
        self.auto_load = kwargs.pop("auto_load", True)


class ApplicationOptions(Options):
    """ Application options """

    def __init__(
            self,
            backend_options: BackendOptions = BackendOptions(),
            window_options: WindowOptions = WindowOptions(),
            docking_options: DockingOptions = DockingOptions(),
            extension_options: ExtensionOptions = ExtensionOptions(),
            **kwargs
    ):
        "Initialize"
        super().__init__()

        # Main
        self.title = kwargs.pop("title", "FARMS")  # FARMS by default
        self.geometry: Iterable[int, int] = kwargs.pop("geometry", [720, 1080])
        self.resizable: bool = kwargs.pop("resizable", True)

        # Imgui Ini options. Imgui uses ini files to save and restore the state of the
        # app and this can be used in conjunction to the FARMS options to either
        # override or save use preferences.

        # Backend options
        self.backend = backend_options

        # Window options
        self.window = window_options

        # Docking options
        self.docking = docking_options

        # Extension options
        self.extension = extension_options

        # FPS
        self.fps = kwargs.pop("fps", 60.0)       # 60 FPS by default

        # Plot options


if __name__ == '__main__':
    opts = ApplicationOptions(
        BackendOptions(),
        WindowOptions(),
        DockingOptions(),
        ExtensionOptions(),
    )
    opts.save("/tmp/app.yaml")
