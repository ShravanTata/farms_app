""" Base class implementation for plugin system """


from abc import ABC, abstractmethod


class BasePlugin(ABC):
    """Plugin base class"""

    @abstractmethod
    def get_name(self) -> str:
        pass

    @abstractmethod
    def render(self) -> None:
        pass
