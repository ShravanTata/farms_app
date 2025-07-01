""" Run """

from farms_core import pylog
from farms_app.core.application import FARMSApplication

pylog.LOGGER.test()
pylog.LOGGER.test()

app = FARMSApplication()
app.run()
