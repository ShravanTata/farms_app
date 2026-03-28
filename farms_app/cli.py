""" Run """


from farms_core import pylog
from farms_app.core.application import FARMSApplication
from farms_app.core.options import ApplicationOptions


pylog.set_level("debug")


def main():
    """ Main Application """
    app_options = ApplicationOptions(title="FARMS-APP", auto_enable=["status_bar",])
    app = FARMSApplication.from_options(app_options)
    app.run()


if __name__ == '__main__':
    main()
