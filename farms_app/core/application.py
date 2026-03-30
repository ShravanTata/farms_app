""" Main script to run the FARMS app """

from typing import List

# from farms_app.core.options import ApplicationOptions
import numpy as np
from farms_app.backends.glfw_impl import OpenGLVersion
from farms_app.backends.manager import BackendManager
from farms_app.backends.base import BaseBackend
from farms_app.console import console
from farms_app.core.extension import ExtensionManager
from farms_app.utils import paths
from farms_core import pylog
from imgui_bundle import imgui, implot
import time

from .options import ApplicationOptions

pylog.set_level("error")


class FARMSApplication:
    """FARMS Application """

    def __init__(self, options: ApplicationOptions):
        """Initialization"""
        super().__init__()

        self._options = options

        # Setup backend
        self.backend: BaseBackend = None
        self._io = None
        self._setup_backend(self._options)
        self.show_metrics_window = True

        self.fps_idle = options.fps_idle
        self.enable_idling = options.enable_idling
        self.is_idling = False

        # Fonts — load JetBrains Mono with FontAwesome icons merged in
        from imgui_bundle import hello_imgui
        font_path = str(paths.get_project_root().joinpath(
            "farms_app", "assets", "fonts", "JetBrainsMono[wght].ttf"
        ))
        hello_imgui.load_font_ttf_with_font_awesome_icons(font_path, 14)

        # Setup extensions
        self.extension_manager = ExtensionManager()

    def _setup_backend(self, options: ApplicationOptions):
        """ Setup backend """
        backend_manager = BackendManager()
        self.backend = backend_manager.initialize(
            backend_type=options.backend.platform,
            gl_version=OpenGLVersion.GL2
        )
        self.backend.initialize(name=options.title)
        self._io = imgui.get_io()
        return backend_manager

    def fps_idling(self):
        """ Idle fps """

        self.is_idling = False
        if ((self.fps_idle > 0.0) and self.enable_idling):

            before_wait = time.time_ns()
            wait_timeout = 1.0 / self.fps_idle

            # Backend specific call that will wait for an event for a maximum duration of waitTimeout
            self.backend.event_timeout(wait_timeout)

            after_wait = time.time_ns()
            wait_duration = (after_wait - before_wait)
            wait_idle_expected = 1.0 / self.fps_idle
            self.is_idling = (wait_duration > wait_idle_expected * 0.9)

    @classmethod
    def from_options(cls, options: ApplicationOptions):
        """ Initialize using options """
        return cls(options)

    def render_menu(self):
        """ Render menu """
        imgui.begin_main_menu_bar()

        # Extension menus (namespaced top-level menus)
        for name, extension in self.extension_manager._enabled_exts.items():
            extension.obj.menu()

        if imgui.begin_menu("View"):
            if imgui.begin_menu("Theme"):
                imgui.show_style_selector("Styles")
                imgui.show_style_editor()
                imgui.end_menu()
            imgui.separator()
            for name, extension in self.extension_manager._enabled_exts.items():
                clicked, new_state = imgui.menu_item(
                    name, shortcut="", p_selected=not extension.obj.hide
                )
                if clicked:
                    extension.obj.hide = not new_state
            imgui.end_menu()

        if imgui.begin_menu("Debug"):
            clicked, new_state = imgui.menu_item("Show Metrics", shortcut="", p_selected=self.show_metrics_window)
            if clicked:
                self.show_metrics_window = new_state
            if imgui.begin_menu("Level"):
                if imgui.menu_item("debug", shortcut="", p_selected=(pylog.get_level()=="debug"))[0]:
                    pylog.set_level("debug")
                if imgui.menu_item("info", shortcut="", p_selected=(pylog.get_level()=="info"))[0]:
                    pylog.set_level("info")
                if imgui.menu_item("warning", shortcut="", p_selected=(pylog.get_level()=="warning"))[0]:
                    pylog.set_level("warning")
                imgui.end_menu()
            imgui.end_menu()

        if imgui.begin_menu("Extensions"):
            for name in self.extension_manager.names:
                clicked, new_state = imgui.menu_item(
                    name, shortcut="", p_selected=True if name in self.extension_manager._enabled_exts else False
                )
                if clicked and new_state:
                    self.extension_manager.enable(name)
                elif clicked and not new_state:
                    self.extension_manager.disable(name)
            imgui.end_menu()
        imgui.end_main_menu_bar()

    def run(self):
        """main run method"""

        _first = True
        _last_time = time.perf_counter()

        while not self.backend.should_close():

            # Frame timing
            now = time.perf_counter()
            dt = now - _last_time
            _last_time = now

            # Idling
            self.fps_idling()

            # Poll events
            self.backend.poll_events()

            # Start the Dear ImGui frame
            self.backend.begin_frame()

            # Render main menu
            self.render_menu()

            if _first:
                for ext_name in self._options.auto_enable:
                    self.extension_manager.enable(ext_name)
                _first = False

            # Tick all extensions: update(dt) -> event() -> render()
            self.extension_manager.tick(dt)

            # End the Dear ImGui frame
            self.backend.end_frame()

        # Cleanup
        self.backend.cleanup()
