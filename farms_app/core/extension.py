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



###########
# Manager #
###########
class ExtensionCategory(StrEnum):
    UI = "ui"
    WORKFLOW = "workflow"
    CUSTOM = "custom"
