""" Main script to run the FARMS app """

import time
from typing import List

# from farms_app.core.options import ApplicationOptions
import numpy as np
from farms_app.backends.base import BaseBackend
from farms_app.backends.glfw_impl import OpenGLVersion
from farms_app.backends.manager import BackendManager
from farms_app.console import console
from farms_app.core.extension import ExtensionManager
from farms_app.core.profiler import FrameTimer
from farms_app.utils import paths
from farms_core import pylog
from imgui_bundle import imgui, implot

from .menus import render_main_menu
from .options import ApplicationOptions


_DEFAULT_OPTIONS_FILE = "options.yaml"


class FARMSApplication:
    """FARMS Application """

    def __init__(self, options: ApplicationOptions, options_path: str = None):
        """Initialization"""
        super().__init__()

        self._options: ApplicationOptions = options
        self._options_path = options_path or _DEFAULT_OPTIONS_FILE

        # Setup backend
        self.backend: BaseBackend = None
        self._io = None
        self._setup_backend(self._options)
        self.show_metrics_window = False

        self.fps_idle = options.fps_idle
        self.enable_idling = options.enable_idling
        self.is_idling = False

        # Fonts — load JetBrains Mono with FontAwesome icons merged in
        from imgui_bundle import hello_imgui
        font_path = str(paths.get_project_root().joinpath(
            "farms_app", "assets", "fonts", options.fonts.name
        ))
        hello_imgui.load_font_ttf_with_font_awesome_icons(font_path, options.fonts.size)

        # Setup extensions
        self.extension_manager = ExtensionManager()

        # Dockspace
        self.dockspace_id: int = 0

        # Frame timer
        self.frame_timer = FrameTimer()
        self.extension_manager.frame_timer = self.frame_timer

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

    @classmethod
    def from_file(cls, path: str = _DEFAULT_OPTIONS_FILE):
        """Load options from YAML and initialize. Falls back to defaults."""
        import os
        if os.path.exists(path):
            options = ApplicationOptions.load(path)
            pylog.info(f"Loaded options from {path}")
        else:
            options = ApplicationOptions()
        return cls(options, options_path=path)

    def render_menu(self):
        """ Render menu """
        render_main_menu(self)

    def run(self):
        """main run method"""

        _first = True
        _last_time = time.perf_counter()

        try:
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
                self.dockspace_id = imgui.dock_space_over_viewport(
                    viewport=imgui.get_main_viewport()
                )

                # Debug
                if self.show_metrics_window:
                    self.show_metrics_window = imgui.show_metrics_window(self.show_metrics_window)

                # Render main menu
                self.render_menu()

                if _first:
                    self.extension_manager.dockspace_id = self.dockspace_id
                    for ext_name in self._options.auto_enable:
                        self.extension_manager.enable(ext_name)
                    self.extension_manager.load_state(self._options.extension.state)
                    _first = False

                # Tick all extensions: update(dt) -> event() -> render()
                self.frame_timer.begin_frame()
                self.extension_manager.tick(dt)
                self.frame_timer.end_frame()
                self.frame_timer.render_overlay()

                # End the Dear ImGui frame
                self.backend.end_frame()
        except KeyboardInterrupt:
            pylog.info("Interrupted — saving state")
        finally:
            # Save extension state into options and write to disk
            self._options.extension.state = self.extension_manager.save_state()
            try:
                self._options.save(self._options_path)
                pylog.info(f"Saved options to {self._options_path}")
            except Exception as e:
                pylog.error(f"Error saving options: {e}")
            self.extension_manager.shutdown()
            self.backend.cleanup()
