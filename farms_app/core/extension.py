""" Extensions management and implementation """

import inspect
import time
from abc import ABC, abstractmethod
from enum import StrEnum
from typing import List, Optional

from farms_app.core.window import BaseWindow, MainExtensionWindow
from farms_core import pylog
from imgui_bundle import imgui
from rich.console import Console
from stevedore import EnabledExtensionManager, extension

EXTENSION_NAMESPACE = "farms.app.extension"


###########
# Manager #
###########
class ExtensionCategory(StrEnum):
    """Categories for organizing and discovering extensions.

    - UI: Extensions that contribute user interface elements or interactive components.

    - WORKFLOW: Extensions that define or modify execution flow, processing steps, and
    can read/write simulation data, add workflow windows.

    - CUSTOM: Extensions that do not fit into a standard category, often experimental or
    new domains that are outside the core of FARMS.

    """
    UI = "ui"
    WORKFLOW = "workflow"
    CUSTOM = "custom"


class ExtensionManager:
