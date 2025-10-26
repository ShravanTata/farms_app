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


class MainMenuRegistry:
    """
    Central registry for managing application menus.
    Extensions can register menu items through this registry.
    """

    def __init__(self):
        # Dictionary of top-level menus: menu_name -> list of items
        self._menus: Dict[str, List[MenuItemType]] = {}
        # Default menu order
        self._menu_order: List[str] = [
            "File",
            "View",
            "Extensions",
            "Windows",
            "Debug",
            "Help"
        ]

        # Initialize default menus
        for menu_name in self._menu_order:
            self._menus[menu_name] = []


def default_main_menu():
    """ Render default main menu """

    imgui.begin_main_menu_bar()
    for option in DEFAULT_MENU_OPTIONS:
        if imgui.begin_menu(option):
            imgui.end_menu()
    # Add sub-menu options
    if imgui.begin_menu("File"):
        if imgui.menu_item_simple("Quit", shortcut="Alt-Q"):
            pass
        imgui.end_menu()
    imgui.end_main_menu_bar()
