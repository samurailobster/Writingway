import json
import logging
import os


class ConversationManager:
    def __init__(self, file_path="conversations.json"):
        self.file_path = file_path
        self.conversations = {}
        self.last_viewed_chat = None
        self.project_names = []  # Will be populated from workbench
        self.load()

    def load(self):
        if not os.path.exists(self.file_path):
            self._initialize_default()
            return

        try:
            with open(self.file_path, encoding="utf-8") as f:
                data = json.load(f)
            version = data.get("version", 0)
            if version == 0:
                if isinstance(data, dict) and all(isinstance(k, str) and isinstance(v, list) for k, v in data.items()):
                    self.conversations = {k: {"mode": "Writing Coach", "messages": v, "pov_character": None} for k, v in data.items()}
                    self.last_viewed_chat = list(data.keys())[0] if data else "Chat 1"
                else:
                    self._load_v1_format(data) # V1 format will handle basic initialization
            elif version == 1:
                self._load_v1_format(data)
            self._ensure_default_conversation()
        except Exception as e:
            logging.error(f"Error loading conversations: {e}", exc_info=True)
            self._initialize_default()

    def _load_v1_format(self, data):
        self.conversations = {}
        for name, conv in data.get("conversations", {}).items():
            self.conversations[name] = self._normalize_conversation(conv)

        # self.conversations = data.get("conversations", {})
        self.last_viewed_chat = data.get("last_viewed_chat", "Chat 1")
        # Normalize all messages to ensure 'preserve' key exists
        for conv in self.conversations.values():
            if "messages" in conv:
                conv["messages"] = self._normalize_messages(conv["messages"])
            if "pov_character" not in conv:
                conv["pov_character"] = None

    # In _load_v1_format and _initialize_default etc.
    def _normalize_conversation(self, conv_data, default_project=None):
        if isinstance(conv_data, list):  # legacy
            return {
                "mode": "Writing Coach",
                "messages": conv_data,
                "pov_character": None,
                "project_name": default_project
            }

        if not isinstance(conv_data, dict):
            conv_data = {}

        conv_data.setdefault("mode", "Writing Coach")
        conv_data.setdefault("messages", [])
        conv_data.setdefault("pov_character", None)
        conv_data.setdefault("project_name", default_project)
        return conv_data

    def _normalize_messages(self, messages):
        """Ensure messages are in clean dict format."""
        normalized = []
        for msg in messages:
            if isinstance(msg, dict):
                normalized.append({
                    "role": msg.get("role", "unknown"),
                    "content": msg.get("content", "")
                })
            else:
                # Fallback for very old malformed data
                normalized.append({
                    "role": "unknown",
                    "content": str(msg)
                })
        return normalized

    def _ensure_default_conversation(self):
        if not self.conversations:
            self._initialize_default()

    def _initialize_default(self):
        self.conversations = {"Chat 1": {
            "mode": "Writing Coach",
            "messages": [],
            "pov_character": None
            }}
        self.last_viewed_chat = "Chat 1"

    def save(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump({
                    "version": 1,
                    "conversations": self.conversations,
                    "last_viewed_chat": self.last_viewed_chat
                }, f, indent=4)
            logging.debug("Conversations saved successfully")
        except Exception as e:
            logging.error(f"Error saving conversations: {e}", exc_info=True)

    def add_conversation(self, name, mode, pov_character=None, project_name=None):
        if name in self.conversations:
            raise ValueError(f"Conversation '{name}' already exists")
        self.conversations[name] = {
            "mode": mode,
            "messages": [],
            "pov_character": pov_character,
            "project_name": project_name or self._get_current_project_name()
        }
        self.last_viewed_chat = name

    def rename_conversation(self, old_name, new_name):
        if old_name not in self.conversations:
            raise ValueError(f"Conversation '{old_name}' not found")
        if new_name in self.conversations:
            raise ValueError(f"Conversation '{new_name}' already exists")
        self.conversations[new_name] = self.conversations.pop(old_name)
        if self.last_viewed_chat == old_name:
            self.last_viewed_chat = new_name

    def delete_conversation(self, name):
        if name not in self.conversations:
            raise ValueError(f"Conversation '{name}' not found")
        del self.conversations[name]
        if self.last_viewed_chat == name:
            self.last_viewed_chat = list(self.conversations.keys())[0] if self.conversations else None

    def get_conversation_names(self):
        return list(self.conversations.keys())

    def get_conversation(self, name):
        conv = self.conversations.get(name, {})
        return self._normalize_conversation(conv)

    def _get_current_project_name(self):
        # For now fallback; better to pass it in
        return getattr(self, '_current_project', None)

    def update_messages(self, name, messages):
        if name in self.conversations:
            self.conversations[name]["messages"] = messages

    def get_mode(self, name):
        return self.conversations.get(name, {}).get("mode", "Writing Coach")

    def get_pov_character(self, name):
        return self.conversations.get(name, {}).get("pov_character", None)

    def get_icon_path(self, mode):
        return "assets/icons/book.svg" if mode == "Writing Coach" else "assets/icons/user.svg"

    def set_last_viewed(self, name):
        if name in self.conversations:
            self.last_viewed_chat = name

    def update_context_selections(self, name, project_uuids, compendium_paths):
        if name in self.conversations:
            self.conversations[name]["context_selections"] = {
                "project": project_uuids,
                "compendium": compendium_paths
            }

    def get_context_selections(self, name):
        conv = self.get_conversation(name)
        # Default to empty lists if not present
        return conv.get("context_selections", {"project": [], "compendium": []})

    def set_available_projects(self, project_names):
        self.project_names = project_names

    def update_project_for_conversation(self, name: str, project_name: str):
        """One-time assignment for legacy chats."""
        if name in self.conversations:
            self.conversations[name]["project_name"] = project_name
            self.save()
