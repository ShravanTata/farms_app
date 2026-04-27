""" Configurable plot window.

Renders plots based on a PlotWindowConfig — users can add, remove,
and reconfigure plots at runtime via an inline configuration panel.

The extension must provide:
  - extension.registry : DataRegistry
  - extension.view_iteration : int
  - extension.task.timestep : float
  - extension.task.buffer_size : int

X-axis source types:
  - "time"     : implicit normalized time axis [-1, 0]
  - "index"    : array indices [0, N)
  - <registry>  : live or static data from the DataRegistry
"""

from dataclasses import dataclass, field

import numpy as np
from farms_app.core.window import Window
from imgui_bundle import imgui, implot


LAYOUT_TYPES = ["subplots_vertical", "tabs"]

# Special x-source values (not registry keys)
X_STATIC = ["time", "index"]


# Configuration
@dataclass
class ReferenceCurve:
    """A static reference curve drawn as a background line on a plot.

    Use for theoretical baselines (e.g., force-length curves, stability
    boundaries) that don't change with simulation state.
    """
    x: np.ndarray               # precomputed x values
    y: np.ndarray               # precomputed y values
    label: str = ""             # legend label
    color: tuple = ()           # (r, g, b, a) — empty for auto


@dataclass
class PlotConfig:
    """Configuration for a single subplot.

    x_source controls what drives the x-axis:
      - "time"    : normalized time [-1, 0] with ring buffer offset
      - "index"   : array indices
      - ""        : same as "time" (default)
      - any str   : registry key (live or static data source)
    """
    x_source: str = "time"
    y_sources: list[str] = field(default_factory=list)
    title: str = ""
    y_label: str = ""
    reference_curves: list[ReferenceCurve] = field(default_factory=list)


@dataclass
class PlotWindowConfig:
    """Configuration for a plot window."""
    name: str = "Plot"
    layout: str = "subplots_vertical"   # "subplots_vertical", "tabs"
    plots: list[PlotConfig] = field(default_factory=list)


# Window
class PlotWindow(Window):
    """A window that renders plots based on its configuration.

    Data is fetched from the extension's data registry each frame.
    Toggle the config panel with the gear button to add/remove/reconfigure plots.
    """

    def __init__(self, extension, config: PlotWindowConfig):
        super().__init__(config.name, extension)
        self.config = config
        self._plot_to_remove = None
        self._rename_target = None  # PlotConfig being renamed
        self._rename_buf = ""

    def on_render(self):
        if not hasattr(self._extension, 'registry') or not hasattr(self._extension, 'task'):
            imgui.text("Extension does not provide a data registry")
            return
        task = self._extension.task
        if task is None:
            imgui.text("No data loaded")
            return

        # Plots
        if self.config.layout == "tabs":
            self._render_tabs(task)
        else:
            self._render_subplots(task)

        # Rename popup (must be outside plot/menu scope)
        self._render_rename_popup()

        # Window-level context menu (right-click on empty area)
        self._render_window_context_menu()

    # Context menus
    def _render_window_context_menu(self):
        """Right-click on the window background for window-level actions."""
        if imgui.begin_popup_context_window("##plot_window_ctx", imgui.PopupFlags_.mouse_button_right | imgui.PopupFlags_.no_open_over_items):
            if imgui.menu_item_simple("Add Plot"):
                self.config.plots.append(PlotConfig(title=f"Plot {len(self.config.plots) + 1}"))
            if imgui.begin_menu("Layout"):
                for lt in LAYOUT_TYPES:
                    if imgui.menu_item(lt, "", self.config.layout == lt)[0]:
                        self.config.layout = lt
                imgui.end_menu()
            imgui.end_popup()

    def _render_rename_popup(self):
        """Modal popup for renaming a plot."""
        popup_id = "##rename_plot"
        if self._rename_target is not None:
            imgui.open_popup(popup_id)

        if imgui.begin_popup(popup_id):
            if self._rename_target is None:
                imgui.close_current_popup()
                imgui.end_popup()
                return

            imgui.set_keyboard_focus_here()
            changed, self._rename_buf = imgui.input_text(
                "##rename", self._rename_buf,
                imgui.InputTextFlags_.enter_returns_true,
            )
            if changed:
                self._rename_target.title = self._rename_buf
                self._rename_target = None
                imgui.close_current_popup()
            if imgui.is_key_pressed(imgui.Key.escape):
                self._rename_target = None
                imgui.close_current_popup()
            imgui.end_popup()

    def _render_plot_context_menu(self, plot_cfg, plot_index):
        """Right-click context menu for a specific plot."""
        registry = self._extension.registry
        if not imgui.begin_popup_context_item(f"##plot_ctx_{plot_index}"):
            return

        # Rename
        if imgui.menu_item_simple("Rename"):
            self._rename_target = plot_cfg
            self._rename_buf = plot_cfg.title

        imgui.separator()

        # X axis source
        if imgui.begin_menu("X Axis"):
            for name in X_STATIC:
                if imgui.menu_item(name, "", plot_cfg.x_source == name)[0]:
                    plot_cfg.x_source = name
            imgui.separator()
            for group_name in registry.groups:
                if imgui.begin_menu(group_name):
                    for source in registry.group(group_name):
                        channel = source.name.rsplit("/", 1)[-1]
                        display = f"{channel} ({source.unit})" if source.unit else channel
                        if imgui.menu_item(display, "", plot_cfg.x_source == source.name)[0]:
                            plot_cfg.x_source = source.name
                    imgui.end_menu()
            imgui.end_menu()

        # Add signals
        if imgui.begin_menu("Add Signal"):
            self._render_source_tree(registry, plot_cfg)
            imgui.end_menu()

        # Remove signals
        if plot_cfg.y_sources and imgui.begin_menu("Remove Signal"):
            to_remove = None
            for j, source_name in enumerate(plot_cfg.y_sources):
                if imgui.menu_item_simple(source_name):
                    to_remove = j
            if to_remove is not None:
                plot_cfg.y_sources.pop(to_remove)
            imgui.end_menu()

        imgui.separator()

        if imgui.menu_item_simple("Remove Plot"):
            self._plot_to_remove = plot_index

        imgui.end_popup()

    def _render_source_tree(self, registry, plot_cfg):
        """Grouped tree of data sources for y-axis selection."""
        for group_name in registry.groups:
            if imgui.begin_menu(group_name):
                items = {}
                for source in registry.group(group_name):
                    parts = source.name.split("/")
                    item_name = parts[1] if len(parts) > 2 else parts[-1]
                    if item_name not in items:
                        items[item_name] = []
                    items[item_name].append(source)

                for item_name, sources in items.items():
                    if imgui.begin_menu(item_name):
                        for source in sources:
                            channel = source.name.rsplit("/", 1)[-1]
                            display = f"{channel} ({source.unit})" if source.unit else channel
                            already = source.name in plot_cfg.y_sources
                            if already:
                                imgui.text_disabled(display)
                            elif imgui.menu_item_simple(display):
                                plot_cfg.y_sources.append(source.name)
                        imgui.end_menu()
                imgui.end_menu()

    # Plot rendering
    _MIN_SUBPLOT_HEIGHT = 120
    _REF_ALPHA = 0.4

    def _render_reference_curves(self, plot_cfg: PlotConfig):
        """Draw static reference curves as dimmed background lines."""
        for ref in plot_cfg.reference_curves:
            spec = implot.Spec()
            if ref.color:
                spec.line_color = imgui.ImVec4(*ref.color)
            else:
                spec.line_color = imgui.ImVec4(0.7, 0.7, 0.7, self._REF_ALPHA)

            x = np.ascontiguousarray(ref.x, dtype=np.float64)
            y = np.ascontiguousarray(ref.y, dtype=np.float64)
            label = ref.label if ref.label else f"##ref_{id(ref)}"
            implot.plot_line(label, x, y, spec)

    def _push_plot_style(self):
        """Push shared aesthetic overrides for all plots."""
        implot.push_style_var(implot.StyleVar_.plot_padding, imgui.ImVec2(8, 6))
        implot.push_style_var(implot.StyleVar_.label_padding, imgui.ImVec2(4, 2))
        implot.push_style_var(implot.StyleVar_.plot_border_size, 0.0)
        implot.push_style_var(implot.StyleVar_.minor_alpha, 0.15)
        implot.push_style_color(implot.Col_.plot_bg, imgui.ImVec4(0.0, 0.0, 0.0, 0.0))
        implot.push_style_color(implot.Col_.axis_grid, imgui.ImVec4(0.5, 0.5, 0.5, 0.15))

    def _pop_plot_style(self):
        implot.pop_style_color(2)
        implot.pop_style_var(4)

    def _render_subplots(self, task):
        plots = self.config.plots
        if not plots:
            imgui.text("No plots configured — right-click to add")
            return

        all_time = all(p.x_source in ("time", "") for p in plots)
        flags = implot.SubplotFlags_.no_title | implot.SubplotFlags_.share_items
        if all_time:
            flags |= implot.SubplotFlags_.link_all_x

        avail_h = imgui.get_content_region_avail().y
        total_h = max(avail_h, len(plots) * self._MIN_SUBPLOT_HEIGHT)
        needs_scroll = total_h > avail_h

        if needs_scroll:
            imgui.begin_child(
                f"##{self._window_id}_scroll",
                imgui.ImVec2(-1, -1),
            )

        self._plot_to_remove = None
        self._push_plot_style()
        try:
            if implot.begin_subplots(
                f"##{self._window_id}_subplots",
                rows=len(plots), cols=1,
                size=imgui.ImVec2(-1, total_h),
                flags=flags,
            ):
                for i, plot_cfg in enumerate(plots):
                    self._render_plot(plot_cfg, task, i)
                implot.end_subplots()
        finally:
            self._pop_plot_style()
            if needs_scroll:
                imgui.end_child()

        if self._plot_to_remove is not None and self._plot_to_remove < len(plots):
            self.config.plots.pop(self._plot_to_remove)

    def _render_tabs(self, task):
        self._plot_to_remove = None
        self._push_plot_style()
        if imgui.begin_tab_bar(f"##{self._window_id}_tabs"):
            for i, plot_cfg in enumerate(self.config.plots):
                if imgui.begin_tab_item(f"{plot_cfg.title or 'Plot'}##tab_{i}")[0]:
                    self._render_plot(plot_cfg, task, i)
                    imgui.end_tab_item()
            imgui.end_tab_bar()
        self._pop_plot_style()

        if self._plot_to_remove is not None and self._plot_to_remove < len(self.config.plots):
            self.config.plots.pop(self._plot_to_remove)

    # Unified plot renderer
    def _render_plot(self, plot_cfg: PlotConfig, task, plot_index: int = 0):
        registry = self._extension.registry
        iteration = self._extension.view_iteration
        buf_size = task.buffer_size

        x_src = plot_cfg.x_source or "time"
        is_time = x_src == "time"
        is_index = x_src == "index"
        is_data = not is_time and not is_index

        title = f"{plot_cfg.title}##{self._window_id}_{id(plot_cfg)}"
        plot_flags = implot.Flags_.no_title

        if implot.begin_plot(title, flags=plot_flags):
            # X axis setup
            if is_time:
                implot.setup_axis(
                    implot.ImAxis_.x1, "",
                    flags=implot.AxisFlags_.lock | implot.AxisFlags_.no_label,
                )
                implot.setup_axis_limits(implot.ImAxis_.x1, -1.0, 0.0, implot.Cond_.always)
            elif is_index:
                implot.setup_axis(
                    implot.ImAxis_.x1, "index",
                    flags=implot.AxisFlags_.auto_fit,
                )
            else:
                x_label = x_src.rsplit("/", 1)[-1]
                implot.setup_axis(implot.ImAxis_.x1, x_label)

            # Y axis
            y_label = plot_cfg.y_label if plot_cfg.y_label else ""
            implot.setup_axis(
                implot.ImAxis_.y1, y_label,
                flags=implot.AxisFlags_.range_fit,
            )

            # Legend
            implot.setup_legend(
                implot.Location_.north_west,
                implot.LegendFlags_.horizontal,
            )

            # Title annotation
            if plot_cfg.title:
                implot.push_style_color(implot.Col_.inlay_text, imgui.ImVec4(0.7, 0.7, 0.7, 0.8))
                implot.annotation(
                    implot.get_plot_limits().x.min * 0.99,
                    implot.get_plot_limits().y.max,
                    imgui.ImVec4(0, 0, 0, 0),
                    imgui.ImVec2(4, 4), False, plot_cfg.title,
                )
                implot.pop_style_color()

            # Reference curves (static backgrounds)
            self._render_reference_curves(plot_cfg)

            # Resolve x data
            ring_offset = int(iteration) % buf_size
            x_data = None

            if is_data:
                x_source = registry.get(x_src)
                if x_source is not None:
                    x_data = np.ascontiguousarray(x_source.accessor())

            # Plot each y source
            for source_name in plot_cfg.y_sources:
                source = registry.get(source_name)
                if source is None:
                    continue

                y_data = np.ascontiguousarray(source.accessor())
                label = source_name.rsplit("/", 1)[-1]

                if is_time:
                    # Single-array overload with xscale/xstart, ring buffer offset
                    xscale = 1.0 / buf_size
                    xstart = -1.0
                    spec = implot.Spec()
                    spec.offset = ring_offset
                    implot.plot_line(label, y_data, xscale, xstart, spec)

                elif is_index:
                    # Plot against array indices with ring buffer offset
                    spec = implot.Spec()
                    spec.offset = ring_offset
                    implot.plot_line(label, y_data, 1.0, 0.0, spec)

                elif x_data is not None:
                    # XY: live data with ring buffer offset
                    spec = implot.Spec()
                    spec.offset = ring_offset
                    implot.plot_line(f"{label}##line", x_data, y_data, spec)

                    # Current position marker
                    cur_idx = (ring_offset - 1) % buf_size
                    implot.plot_scatter(
                        f"{label}##now",
                        np.array([float(x_data[cur_idx])], dtype=np.float64),
                        np.array([float(y_data[cur_idx])], dtype=np.float64),
                    )

            implot.end_plot()
            self._render_plot_context_menu(plot_cfg, plot_index)
