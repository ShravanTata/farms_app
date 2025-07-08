""" Run """

from farms_core import pylog
from farms_app.core.application import FARMSApplication

pylog.set_level("debug")

app = FARMSApplication()
app.run()
