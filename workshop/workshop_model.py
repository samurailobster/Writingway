from .conversation_manager import ConversationManager
from .embedding_manager import EmbeddingIndex

class WorkshopModel:
    def __init__(self, parent_model=None, project_name=None):
        self.project_name = project_name or getattr(parent_model, "project_name", "DefaultProject")
        self.structure = getattr(parent_model, "structure", {"acts": []}) if parent_model else {"acts": []}
        self.conversation_manager = ConversationManager()
        self.conversation_manager.set_available_projects(self.get_available_projects())
        self.embedding_index = EmbeddingIndex()

    def get_available_projects(self):
        """Get list of project names from workbench"""
        try:
            from workbench import PROJECTS
            return [p["name"] for p in PROJECTS]
        except:
            return [self.project_name]
        
    def load_project_structure(self, project_name: str):
        if project_name == self.project_name and self.structure:
            return self.structure
        from workshop.project_context_provider import ProjectContextProvider
        provider = ProjectContextProvider(project_name)
        return provider.get_structure()