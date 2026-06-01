## file: chat_session.py
import logging

from .conversation_history_manager import estimate_conversation_tokens, summarize_conversation

TOKEN_LIMIT = 3500

class BaseChatSession:
    def __init__(self, mode, messages, context_panel, prompt_panel, embedding_index):
        self.mode = mode
        self.messages = messages
        self.context_panel = context_panel
        self.prompt_panel = prompt_panel
        self.embedding_index = embedding_index

    def validate(self)-> bool:
        return True

    def get_system_prompt(self, prompt_config, compendium_text, story_text):
        return prompt_config.get("text", "")

    def augment_user_message(self, user_input, story_text, retrieved_context):
        augmented = user_input
        if story_text:
            augmented += f"\n\nStory Context:\n{story_text}"
        if retrieved_context:
            augmented += "\n\n[Retrieved Context]:\n" + "\n".join(retrieved_context)
        return augmented

    def construct_message(self, user_input):
        if not user_input:
            return None
        prompt_config = self.prompt_panel.get_prompt()
        overrides = self.prompt_panel.get_overrides() if prompt_config else {}
        compendium_text = self.context_panel.get_selected_compendium_text()
        story_text = self.context_panel.get_selected_story_text()
        system_prompt = self.get_system_prompt(prompt_config, compendium_text, story_text)
        retrieved_context = self.embedding_index.query(user_input)
        augmented_message = self.augment_user_message(user_input, story_text, retrieved_context)
        payload = list(self.messages)
        payload.append({"role": "system", "content": system_prompt})
        payload.append({"role": "user", "content": augmented_message})
        if estimate_conversation_tokens(payload) > TOKEN_LIMIT:
            # Keep last 2 messages from history + current user message out of summarization
            history_to_summarize = payload[:-4] if len(payload) > 4 else []  # exclude last 2 history + new user msg
            summary = summarize_conversation(history_to_summarize, overrides=overrides)

            # Rebuild payload with summary + fresh user input
            payload = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"""[Conversation Summary]
{summary}

[Recent Context]
{self._format_last_messages(payload[-4:-2]) if len(payload) > 3 else ""}

[Current Request]
{augmented_message}"""}
            ]
        logging.debug(f"Constructed payload: {len(payload)} messages, ~{estimate_conversation_tokens(payload)} tokens\n\n{payload}")
        return payload

    def _format_last_messages(self, messages):
        """Helper to show last messages clearly in the prompt."""
        formatted = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            formatted.append(f"{role}: {content}")
        return "\n".join(formatted)

    def append_message(self, role, content):
        self.messages.append({"role": role, "content": content})

    def get_preview_payload(self, view):
        user_input = view.chat_input.toPlainText().strip()  # Assuming access via context_panel
        return self.construct_message(user_input)

    def mark_last_exchange_as_edited(self):
        """Mark the most recent User + Assistant pair as edited (for visual strikeout)."""
        messages = self.messages
        if len(messages) >= 2 and messages[-2].get("role") == "user":
            messages[-2]["edited"] = True
            if len(messages) > 2 and messages[-1].get("role") == "assistant":
                messages[-1]["edited"] = True

class WritingCoachSession(BaseChatSession):
    def __init__(self, messages, context_panel, prompt_panel, embedding_index):
        super().__init__("Writing Coach", messages, context_panel, prompt_panel, embedding_index)

class RolePlaySession(BaseChatSession):
    def __init__(self, messages, context_panel, prompt_panel, embedding_index):
        super().__init__("Role Play", messages, context_panel, prompt_panel, embedding_index)

    def validate(self) -> bool:
        compendium_text = self.context_panel.get_selected_compendium_text()
        if not compendium_text:
            return False
        return True

    def get_system_prompt(self, prompt_config, compendium_text, story_text):
        system_prompt = super().get_system_prompt(prompt_config, compendium_text, story_text)
        system_prompt += " Character details:\n{character_details}"
        return system_prompt.format(character_details=compendium_text)
