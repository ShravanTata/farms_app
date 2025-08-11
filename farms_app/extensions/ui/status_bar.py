""" Statu Bar """

from farms_app.extensions.base import UIExtension

from imgui_bundle import imgui


class StatusBarExtension(UIExtension):
    """ Status bar for the app """

    def __init__(self):
        self.show_window = True
        self.window_name = "StatusBar"

    def render(self) -> None:
        if self.show_window:
            imgui_io = imgui.get_io()
            window_flags = (
                imgui.WindowFlags_.no_title_bar |
                imgui.WindowFlags_.no_resize |
                imgui.WindowFlags_.no_move |
                imgui.WindowFlags_.no_scrollbar |
                imgui.WindowFlags_.no_collapse
            )

            viewport = imgui.get_main_viewport()
            imgui.push_style_var(imgui.StyleVar_.window_padding, imgui.ImVec2((0.0, 0.0)))
            imgui.internal.begin_viewport_side_bar(
                "##sidebar", viewport, imgui.Dir.down, imgui.get_frame_height(), window_flags
            )
            imgui.text(f"©FARMS")
            imgui.same_line(imgui_io.display_size.x - 5.0 * imgui.get_font_size())
            imgui.text(f"FPS: {imgui_io.framerate:.1f}")
            imgui.end()
            imgui.pop_style_var()
