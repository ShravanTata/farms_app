""" Base interface for backend """


from abc import ABC, abstractmethod
from typing import Any

from imgui_bundle import imgui


class BackendError(Exception):
    """Backend-specific errors"""
    pass


class BaseBackend(ABC):
    """Abstract base class for all backends"""

    @abstractmethod
    def initialize(self, name: str, width: int, height: int, **kwargs) -> Any:
        """Initialize the backend and return window handle"""
        pass

    @abstractmethod
    def cleanup(self):
        """Cleanup backend resources"""
        pass

    @abstractmethod
    def begin_frame(self):
        """Begin frame rendering"""
        pass

    @abstractmethod
    def end_frame(self):
        """End frame rendering"""
        pass

    @abstractmethod
    def draw(self, data: imgui.ImDrawData):
        """ valid after Render() and until the next call to NewFrame(). this is what you have to render. """
        pass

    @abstractmethod
    def should_close(self) -> bool:
        """Check if window should close"""
        pass

    @abstractmethod
    def poll_events(self):
         """Poll events"""
         pass
