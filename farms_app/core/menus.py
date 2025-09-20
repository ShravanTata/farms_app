""" Main application level menus """


from imgui_bundle import imgui


DEFAULT_MENU_OPTIONS = (
    "File",
    "View",
    "Extensions",
    "Windows",
    "Debug",
    "Help",
)


def default_main_menu():
    """ Render default main menu """

    imgui.begin_main_menu_bar()

    for option in DEFAULT_MENU_OPTIONS:
        if imgui.begin_menu(option):
            pass
            imgui.end_menu()

    imgui.end_main_menu_bar()
