""" Main script to run the FARMS app """

from typing import List

# from farms_app.core.options import ApplicationOptions
import numpy as np
from farms_app.backends.glfw_impl import OpenGLVersion
from farms_app.backends.manager import BackendManager
from farms_app.console import console
from farms_app.core.extension import ExtensionCategory, ExtensionManager
from farms_app.core.menus import default_main_menu
from farms_app.utils import paths
from farms_core import pylog
from imgui_bundle import imgui, implot

from .options import ApplicationOptions

pylog.set_level("debug")


class FARMSApplication:
    """FARMS Application """

    def __init__(self, options: ApplicationOptions):
        """Initialization"""
        super().__init__()

        self._options = options

        # Setup backend
        self.backend = None
        self._window = None
        self._io = None
        self._setup_backend(self._options)
        self.show_metrics_window = True

        self._run_disable_extension = False

        # Fonts
        self._io.fonts.add_font_from_file_ttf(
            str(paths.get_project_root().joinpath(
                "farms_app", "assets", "fonts", "JetBrainsMono[wght].ttf"
            )),
            14
        )

        # Setup extensions
        self.extension_manager = ExtensionManager()

    def _setup_backend(self, options: ApplicationOptions):
        """ Setup backend """
        backend_manager = BackendManager()
        self.backend = backend_manager.initialize(
            backend_type="glfw",
            gl_version=OpenGLVersion.GL2
        )
        self.backend.initialize(name=self._options.title)
        self._window = self.backend.window
        self._io = imgui.get_io()
        return backend_manager

    @classmethod
    def from_options(cls, options: ApplicationOptions):
        """ Initialize using options """
        return cls(options)

    def render_extensions(self):
        for name, extension in self.extension_manager._enabled_exts.items():
            if extension.category == ExtensionCategory.UI:
                extension.obj.render()
            elif extension.category == ExtensionCategory.WORKFLOW:
                extension.obj.render()
            elif extension.category == ExtensionCategory.CUSTOM:
                extension.obj.render()
            # render menu
            try:
                if extension.obj.is_focused:
                    extension.obj.render_menu()
            except:
                pass

    def render_menu(self):
        """ Render menu """
        imgui.begin_main_menu_bar()

        if imgui.begin_menu("View"):
            if imgui.begin_menu("Theme"):
                imgui.show_style_selector("Styles")
                imgui.show_style_editor()
                imgui.end_menu()
            if imgui.begin_menu("UI"):
                for name, extension in self.extension_manager._enabled_exts.items():
                    if extension.category == ExtensionCategory.UI:
                        clicked, new_state = imgui.menu_item(
                            name, shortcut="", p_selected=extension.obj.show_window
                        )
                        if clicked:
                            extension.obj.show_window = new_state
                imgui.end_menu()
            imgui.separator()
            if imgui.begin_menu("Workflow"):
                for name, extension in self.extension_manager._enabled_exts.items():
                    if extension.category == ExtensionCategory.WORKFLOW:
                        clicked, new_state = imgui.menu_item(
                            name, shortcut="", p_selected=extension.obj.show_window
                        )
                        if clicked:
                            extension.obj.show_window = new_state
                imgui.end_menu()
            imgui.separator()
            if imgui.begin_menu("Custom"):
                for name, extension in self.extension_manager._enabled_exts.items():
                    if extension.category == ExtensionCategory.CUSTOM:
                        clicked, new_state = imgui.menu_item(
                            name, shortcut="", p_selected=extension.obj.show_window
                        )
                        if clicked:
                            extension.obj.show_window = new_state
                imgui.end_menu()
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
                    self.extension_manager._disabled_exts.append(name)
                    self._run_disable_extension = True
            imgui.end_menu()
        # Run this after the menu is closed
        if self._run_disable_extension:
            for name in self.extension_manager._disabled_exts:
                self.extension_manager.disable(name)
            self._run_disable_extension = False
        imgui.end_main_menu_bar()

    def run(self):
        """main run method"""

        while not self.backend.should_close():
            # Poll events
            self.backend.poll_events()

            # Start the Dear ImGui frame
            self.backend.begin_frame()

            # Render main menu
            self.render_menu()
            default_main_menu()

            if self.show_metrics_window:
                imgui.show_metrics_window()

            # Render extensions
            self.render_extensions()

            # End the Dear ImGui frame
            self.backend.end_frame()

        # Cleanup
        self.backend.cleanup()
