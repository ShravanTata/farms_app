from enum import Enum
from typing import Optional

from farms_core import pylog

from .base import BaseBackend
from .glfw_impl import GLFWBackend


class PlatformType(Enum):
    """ Type of Platform """
    GLFW = 1


class RendererType(Enum):
    """ Type of Renderer """
    OPENGL2 = 1
    OPENGL3 = 2


class BackendManager:
    """Manages different backend implementations"""

    def __init__(self):
        self.current_backend: Optional[BaseBackend] = None
        self._available_backends = {
            'glfw': GLFWBackend,
        }

    def create_backend(self, backend_type: str = 'glfw', **kwargs) -> BaseBackend:
        """Create a backend instance"""
        if backend_type not in self._available_backends:
            raise pylog.error(f"Unknown backend: {backend_type}")

        backend_class = self._available_backends[backend_type]
        return backend_class(**kwargs)

    def initialize(self, backend_type: str = 'glfw', **kwargs) -> BaseBackend:
        """Initialize and set current backend"""
        if self.current_backend:
            self.current_backend.cleanup()

        self.current_backend = self.create_backend(backend_type, **kwargs)
        return self.current_backend

    def cleanup(self):
        """Cleanup current backend"""
        if self.current_backend:
            self.current_backend.cleanup()
            self.current_backend = None
