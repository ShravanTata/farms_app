""" Layout utilities for docking windows.

Thin wrapper around imgui.internal.dock_builder_* to keep
extension code clean and insulated from internal API details.
"""

from imgui_bundle import imgui


def is_first_use(dockspace_id: int) -> bool:
    """True when the dockspace has no layout yet (no imgui.ini loaded)."""
    node = imgui.internal.dock_builder_get_node(dockspace_id)
    if node is None:
        return True
    return node.is_leaf_node


def split(node_id: int, direction: imgui.Dir, ratio: float) -> tuple:
    """Split a dock node. Returns (id_at_direction, id_opposite)."""
    _, id_at_dir, id_opposite = imgui.internal.dock_builder_split_node_py(
        node_id, direction, ratio
    )
    return id_at_dir, id_opposite


def dock_window(window_id: str, node_id: int):
    """Assign a window to a dock node."""
    imgui.internal.dock_builder_dock_window(window_id, node_id)


def finish(node_id: int):
    """Finalize the dock builder layout."""
    imgui.internal.dock_builder_finish(node_id)
