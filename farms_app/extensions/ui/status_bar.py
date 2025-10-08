""" Status Bar """

from farms_app.core.extension import UIExtension
from farms_app.core.window import BaseWindow

from imgui_bundle import imgui


class StatusBarExtension(UIExtension):
    """ Status bar for the app """

    def __init__(self):
        name = "StatusBar"
        super().__init__(name=name)
        self.register_window(StatusBarWindow(self))

    def get_dependencies(self):
        """ Get extension dependencies """

    def cleanup(self):
        """ Cleanup resources before unloading the extension """


class StatusBarWindow(BaseWindow):
    """ Render Status Bar """

    def __init__(self, extension) -> None:
        name: str = "statusbar"
        window_flags = (
            imgui.WindowFlags_.no_title_bar |
            imgui.WindowFlags_.no_resize |
            imgui.WindowFlags_.no_move |
            imgui.WindowFlags_.no_scrollbar |
            imgui.WindowFlags_.no_collapse |
            imgui.WindowFlags_.no_scroll_with_mouse |
            imgui.WindowFlags_.no_bring_to_front_on_focus |
            imgui.WindowFlags_.no_nav_focus
        )
        super().__init__(
            name=name,
            extension=extension,
            window_flags=window_flags,
            visible=True,
            dock_to_extension=False
        )

    def on_initialize(self):
        """ On initialize """

    def on_update(self):
        """ On update """

    def on_render(self):
        """ Render main extension dockspace """
        imgui_io = imgui.get_io()
        font_size = imgui.get_font_size()
        dy = font_size * 0.15

        viewport = imgui.get_main_viewport()
        imgui.push_style_var(imgui.StyleVar_.window_padding, imgui.ImVec2((0.0, 0.0)))
        imgui.internal.begin_viewport_side_bar(
            "##sidebar", viewport, imgui.Dir.down, 1.0*imgui.get_frame_height(), self._window_flags
        )
        imgui.text(f"©FARMS")
        imgui.same_line(imgui_io.display_size.x - 15.0 * font_size)
        imgui.checkbox("Enable idling", True)
        imgui.same_line()
        imgui.set_cursor_pos_y(imgui.get_cursor_pos_y() - dy)
        imgui.text(f"FPS: {imgui_io.framerate:.1f}")
        imgui.end()
        imgui.pop_style_var()
