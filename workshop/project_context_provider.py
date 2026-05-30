# workshop/project_context_provider.py


class ProjectContextProvider:
    """
    Lightweight provider that gives ContextPanel what it needs
    without tight coupling to Workshop or full ProjectModel.
    """

    def __init__(self, project_name: str):
        self.project_name = project_name

    def get_structure(self) -> dict:
        """Return lightweight project structure (acts/chapters/scenes)."""
        from project_window.tree_manager import load_structure
        return load_structure(self.project_name)

    def get_scene_content(self, hierarchy: list[str]) -> str | None:
        """Lazy-load scene content when requested."""
        try:
            from project_window.project_model import ProjectModel
            model = ProjectModel(self.project_name)
            content = model.load_scene_content(hierarchy)
            return content
        except Exception as e:
            print(f"Failed to load scene content for {hierarchy}: {e}")
            return None

    def get_summary_content(self, hierarchy: list[str]) -> str | None:
        """Load summary content."""
        try:
            from project_window.project_model import ProjectModel
            model = ProjectModel(self.project_name)
            return model.load_summary(hierarchy=hierarchy)
        except Exception:
            return None
