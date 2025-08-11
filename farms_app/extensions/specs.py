import pluggy


hookspec = pluggy.HookspecMarker("farms-app")


class AppWidgetSpec:
    """Full access - internal app components like status bar, menu bar"""
    def __init__(self, app_context):
        super().__init__()
        self.app_context = app_context  # Full access

    @hookspec
    def render(self):
        pass
