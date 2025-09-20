""" Extensions management and implementation """


import inspect
import traceback
from abc import ABC
from enum import StrEnum
from typing import Type
from rich.console import Console

from farms_core import pylog
from stevedore import DriverManager, EnabledExtensionManager, extension

from .base import (BaseExtension, CustomExtension, UIExtension,
                   WorkflowExtension)


###########
# Manager #
###########
class ExtensionCategory(StrEnum):
    UI = "ui"
    WORKFLOW = "workflow"
    CUSTOM = "custom"
