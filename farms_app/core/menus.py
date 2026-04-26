""" Main application level menus """

from farms_core import pylog
from imgui_bundle import imgui


def render_main_menu(app):
    """Render the main menu bar.

    Args:
        app: FARMSApplication instance.
    """
    imgui.begin_main_menu_bar()

    # File
    if imgui.begin_menu("File"):
        if imgui.menu_item_simple("Quit", shortcut="Alt+Q"):
            app.backend.request_close()
        imgui.end_menu()

    # View
    if imgui.begin_menu("View"):
        if imgui.begin_menu("Theme"):
            imgui.show_style_selector("Styles")
            imgui.show_style_editor()
            imgui.end_menu()
        imgui.separator()
        if imgui.begin_menu("Extensions"):
            for name, extension in app.extension_manager._enabled_exts.items():
                clicked, new_state = imgui.menu_item(
                    name, shortcut="", p_selected=not extension.obj.hide
                )
                if clicked:
                    extension.obj.hide = not new_state
            imgui.end_menu()
        imgui.end_menu()

    # Extensions
    if imgui.begin_menu("Extensions"):
        for name in app.extension_manager.names:
            clicked, new_state = imgui.menu_item(
                name, shortcut="",
                p_selected=name in app.extension_manager._enabled_exts,
            )
            if clicked and new_state:
                app.extension_manager.enable(name)
            elif clicked and not new_state:
                app.extension_manager.disable(name)
        imgui.end_menu()

    # Debug
    if imgui.begin_menu("Debug"):
        clicked, new_state = imgui.menu_item(
            "Show Metrics", shortcut="", p_selected=app.show_metrics_window
        )
        if clicked:
            app.show_metrics_window = new_state
        clicked, new_state = imgui.menu_item(
            "Frame Timer", shortcut="", p_selected=app.frame_timer.enabled
        )
        if clicked:
            app.frame_timer.enabled = new_state
        if imgui.begin_menu("Level"):
            for level in ("debug", "info", "warning"):
                if imgui.menu_item(
                    level, shortcut="",
                    p_selected=(pylog.get_level() == level),
                )[0]:
                    pylog.set_level(level)
            imgui.end_menu()
        imgui.end_menu()

    # Help
    if imgui.begin_menu("Help"):
        imgui.menu_item_simple("About FARMS App")
        imgui.end_menu()

    # Extension-contributed top-level menus
    for name, extension in app.extension_manager._enabled_exts.items():
        extension.obj.menu()

    imgui.end_main_menu_bar()
