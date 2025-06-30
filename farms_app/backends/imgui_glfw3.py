import platform
import sys

from imgui_bundle import imgui
import OpenGL.GL as GL  # type: ignore
# Always import glfw *after* imgui_bundle
# (since imgui_bundle will set the correct path where to look for the correct version of the glfw dynamic library)
import glfw  # type: ignore


def glfw_error_callback(error: int, description: str) -> None:
    sys.stderr.write(f"Glfw Error {error}: {description}\n")


def create_window(name: str="FARMS", width: int=1280, height: int=720, **kwargs):
    """ Create GLFW window """
    glfw.set_error_callback(glfw_error_callback)
    if not glfw.init():
        print("Could not initialize OpenGL context")
        sys.exit(1)

    if platform.system() == "Darwin":
        glsl_version = "#version 150"
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, kwargs.pop("VERSION_MAJOR", 1))
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, kwargs.pop("VERSION_MINOR", 0))
        # glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)  # // 3.2+ only
        # glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, GL.GL_TRUE)
    else:
        # GL 3.0 + GLSL 130
        glsl_version = "#version 130"
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, kwargs.pop("VERSION_MAJOR", 3))
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, kwargs.pop("VERSION_MINOR", 0))
        # glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE) # // 3.2+ only
        # glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, GL_TRUE)

    # Create a windowed mode window and its OpenGL contextg
    window = glfw.create_window(int(width), int(height), name, None, None)
    glfw.make_context_current(window)
    glfw.swap_interval(1)  # // Enable vsync

    if not window:
        glfw.terminate()
        print("Could not initialize Window")
        sys.exit(1)

    return window


def setup_imgui_context(window, glsl_version):
    # Setup Dear ImGui context
    # IMGUI_CHECKVERSION();
    imgui.create_context()
    io = imgui.get_io()
    io.config_flags |= (
        imgui.ConfigFlags_.nav_enable_keyboard.value
    )  # Enable Keyboard Controls
    # io.config_flags |= imgui.ConfigFlags_.nav_enable_gamepad # Enable Gamepad Controls
    io.config_flags |= imgui.ConfigFlags_.docking_enable.value  # Enable docking
    io.config_flags |= imgui.ConfigFlags_.viewports_enable # Enable Multi-Viewport / Platform Windows
    io.config_viewports_no_auto_merge = False
    io.config_viewports_no_task_bar_icon = True

    # Setup Dear ImGui style
    imgui.style_colors_dark()
    # imgui.style_colors_classic()

    # When viewports are enabled we tweak WindowRounding/WindowBg so platform windows can look identical to regular ones.
    style = imgui.get_style()
    if io.config_flags & imgui.ConfigFlags_.viewports_enable.value:
        style.window_rounding = 0.0
        window_bg_color = style.color_(imgui.Col_.window_bg.value)
        window_bg_color.w = 1.0
        style.set_color_(imgui.Col_.window_bg.value, window_bg_color)

    # Setup Platform/Renderer backends
    import ctypes

    # You need to transfer the window address to imgui.backends.glfw_init_for_opengl
    # proceed as shown below to get it.
    window_address = ctypes.cast(window, ctypes.c_void_p).value
    assert window_address is not None
    imgui.backends.glfw_init_for_opengl(window_address, True)

    imgui.backends.opengl2_init()


def initialize(name: str="FARMS", width: int=1280, height: int=720):

    window = create_window(name, width, height)
    setup_imgui_context(window, glsl_version="#version 150")

    return window
