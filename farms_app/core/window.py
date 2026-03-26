""" Window """


from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, Optional

from farms_app.console import console
from farms_app.extensions.base import BaseExtension
from farms_core import pylog
from imgui_bundle import imgui


class WindowManager:
    """Slim window registry. Will grow into layout persistence."""

    def __init__(self):
        self.windows: list[BaseWindow] = []

    def register(self, window: "BaseWindow") -> None:
        self.windows.append(window)

    def unregister(self, window: "BaseWindow") -> None:
        if window in self.windows:
            self.windows.remove(window)


class BaseWindow(ABC):
    """ Base Window """

    def __init__(
            self, name: str,
            extension: BaseExtension,
            window_flags: imgui.WindowFlags_ = imgui.WindowFlags_.none,
            visible: bool = True,
            dock_to_extension: bool = True
    ):
        """
        Args:
            name: Window name (will be made unique with extension name)
            extension: Parent extension
            window_flags: ImGui window flags
            visible: Initial visibility state
            dock_to_extension: Whether to dock to extension's dockspace initially

        Lifecycle
        ---------
        1. Construction  — sets up IDs and flags, no imgui calls.
        2. initialize()  — called explicitly by the extension after it has set up
                       its own context (e.g. state, runner).  Safe to call any
                       imgui API here since the manager guarantees a valid frame.
        3. _render()     — called every frame by ExtensionManager.tick_app().
                       Guards on _initialized and _visible before touching imgui.
        """

        self.name: str = name
        self._extension: BaseExtension = extension
        # Check if the window name already exists in the extension
        self._window_id: str = self.create_window_id(self._extension.name, self.name)
        self._window_flags: imgui.WindowFlags_ = window_flags

        # Window state
        self._initialized: bool = False
        self._visible: bool = visible
        self._should_dock_to_extension: bool = dock_to_extension

        # Window properties that can be saved/restored
        self._window_size: Optional[tuple[float, float]] = None
        self._window_pos: Optional[tuple[float, float]] = None

    def initialize(self):
        """Initialize the window - called once after creation"""
        if self._initialized:
            return

        try:
            self.on_initialize()
            self._initialized = True
        except Exception as e:
            console.print_exception()
            pylog.error(f"Error initializing window {self._window_id}: {e}")

    @abstractmethod
    def on_initialize(self):
        """ Initialize """

    @abstractmethod
    def on_render(self):
        """ Render content for the window """

    # @abstractmethod
    # def on_event(self):
    #     """ Enter on events such as mouse or keyboard """

    def _render(self) -> None:
        """ Internal main render call """
        if imgui.begin(self._window_id, flags=self._window_flags):
            self.on_render()
        imgui.end()

    # Properties for window state management
    @property
    def visible(self) -> bool:
        """ Get if current window is visible or not """
        return self._visible

    @visible.setter
    def visible(self, value: bool) -> None:
        self._visible = value

    @property
    def window_id(self) -> str:
        """ Get window ID """
        return self._window_id

    def show(self) -> None:
        """Show the window"""
        self._visible = True

    def hide(self) -> None:
        """Hide the window"""
        self._visible = False

    def toggle_visibility(self) -> None:
        """Toggle window visibility"""
        self._visible = not self._visible

    def dock_to_extension(self) -> None:
        """Dock window back to extension's dockspace"""
        self._should_dock_to_extension = True

    def set_window_flags(self, window_flags: imgui.WindowFlags_) -> None:
        """Set ImGui window flags"""
        self._window_flags = window_flags

    def set_window_size(self, width: float, height: float) -> None:
        """Set window size"""
        self._window_size = (width, height)

    def set_window_pos(self, x: float, y: float) -> None:
        """Set window position"""
        self._window_pos = (x, y)

    def validate_window(self, extension_manager) -> bool:
        """Validate that window belongs to a loaded extension"""
        if not extension_manager:
            return False
        return self._extension.name in extension_manager.names

    def create_window_id(self, extension: str, name: str) -> str:
        """Create unique window identifier"""
        return f"{name}##{extension}"

    def get_state(self) -> Dict[str, Any]:
        """Get window state for persistence"""
        return {
            'visible': self._visible,
            'size': self._window_size,
            'pos': self._window_pos,
            'dock_to_extension': self._should_dock_to_extension
        }

    def set_state(self, state: Dict[str, Any]) -> None:
        """Restore window state from persistence"""
        self._visible = state.get('visible', True)
        self._window_size = state.get('size')
        self._window_pos = state.get('pos')
        self._should_dock_to_extension = state.get('dock_to_extension', True)


class MainExtensionWindow(BaseWindow):
    """ Main extension window """

    def __init__(self, extension: BaseExtension):
        name: str = f"{extension.name}##main"
        window_flags = (
            imgui.WindowFlags_.menu_bar |
            imgui.WindowFlags_.no_title_bar
        )
        super().__init__(
            name=name,
            extension=extension,
            window_flags=window_flags,
            visible=True,
            dock_to_extension=True
        )
        # Create unique dockspace ID for this extension
        self.dockspace_id = None

        # Initialize main window upon created by default
        self.initialize()

    def on_initialize(self):
        """ On initialize """
        # self.dockspace_id = imgui.get_id(f"{self._extension.name}_dockspace")
        pass

    def _render(self):
        """ Internal main render call """
        if imgui.begin(self._window_id, flags=self._window_flags):
            self.on_render()
        imgui.end()

    def on_render(self):
        """ Render main extension dockspace """
        # Render the extension menu
        self._extension.render_menu()
        # Each window gets its own dockspace ID
        # imgui.dock_space(
        #     self.dockspace_id,
        #     (0.0, 0.0),
        #     imgui.DockNodeFlags_.passthru_central_node
        # )
