#!/usr/bin/env python
"""
text_analysis.py

English-specific text analysis module inheriting from BaseTextAnalysis.
Provides tooltip functionality similar to text_analysis_pl.
"""

import textstat

from .base_text_analysis import BaseTextAnalysis

# Tooltip translations for English, formatted as HTML strings
TOOLTIP_TRANSLATIONS = {
    "complex": """
        <b>Complex sentences</b><br>
        Highlights sentences that are very long or have many clauses, making them hard to follow.<br>
        Consider breaking them into shorter, clearer sentences.
    """,
    "weak": """
        <b>Weak formulations/passive voice</b><br>
        Marks parts of the text where the language is not assertive.<br>
        Includes:<br>
        - Weak formulations (phrases that sound vague or indecisive)<br>
        - Passive voice (sentences where the subject isn't performing the action)<br>
        Example: 'The ball was thrown' vs 'John threw the ball'<br>
        Both can make writing feel less direct and lively.
    """,
    "nonstandard": """
        <b>Non-standard speech verbs</b><br>
        Identifies unusual or uncommon verbs used for speaking<br>
        (instead of common words like 'said').<br>
        These can confuse readers if they're too creative or unfamiliar.
    """,
    "filter": """
        <b>Filter words</b><br>
        Flags words that act as filters – words that soften or obscure the message<br>
        (like 'just,' 'really,' or 'quite').<br>
        Removing them can make your statements stronger and clearer.
    """,
    "telling": """
        <b>Telling not showing</b><br>
        Highlights parts where the text tells what a character feels or does<br>
        instead of showing it through description or action.<br>
        This can make the narrative less engaging.
    """,
    "weak_verb": """
        <b>Weak verbs</b><br>
        Marks verbs that don't convey a strong sense of action or emotion.<br>
        Replacing them with vivid, precise verbs can make writing more dynamic.
    """,
    "overused": """
        <b>Overused words</b><br>
        Identifies words that appear too often, making the text repetitive or dull.<br>
        Consider using synonyms or rephrasing to keep language fresh.
    """,
    "pronoun": """
        <b>Unclear pronoun references</b><br>
        Flags pronouns ('he,' 'she,' 'it,' 'they') with unclear noun references.<br>
        Clear pronoun use is important to avoid confusion.
    """,
    "repetitive": """
        <b>Repetitive sentence starts</b><br>
        Highlights when several sentences begin the same way.<br>
        Varying sentence beginnings helps keep the reader's interest.
    """
}

# Data specific to English text analysis
ENGLISH_DATA = {
    "passive_deps": {"nsubjpass", "auxpass"},
    "agent_markers": {"by"},
    "weak_patterns": [r'\b\w+ly\b'],
    "weak_terms": {"maybe", "perhaps", "possibly", "apparently", "presumably", "i think", "i believe", "it seems", "seemingly", "somewhat", "kind of", "sort of"},
    "standard_speech_verbs": {"say", "ask"},
    "speech_verbs": {"say", "ask", "whisper", "murmur", "breathe", "exclaim", "shout", "chastise"},
    "filter_words": {"saw", "heard", "felt", "noticed", "realized", "thought", "wondered", "watched", "looked", "listened", "smelled", "decided", "considered", "seemed", "appeared", "observed", "sensed", "perceived", "imagined"},
    "telling_verbs": {"be", "feel", "seem", "look", "appear", "become", "get"},
    "emotion_words": {"angry", "sad", "happy", "excited", "nervous", "afraid", "worried", "embarrassed", "disappointed", "frustrated", "annoyed", "anxious", "scared", "terrified", "joyful", "depressed", "miserable", "ecstatic", "upset", "furious", "delighted", "shocked", "surprised", "confused", "proud", "ashamed", "content", "satisfied", "eager", "envious", "jealous"},
    "weak_verbs": {"be"},
    "common_words": {"the", "a", "an", "and", "but", "or", "in", "on", "at", "to", "of", "for", "with", "by", "as", "is", "are", "was", "were", "be", "been", "have", "has", "had", "i", "you", "he", "she", "it", "we", "they", "this", "that", "these", "those", "there", "here", "my", "your", "his", "her", "its", "our", "their"},
    "quote_pattern": r'"[^"]*"'
}

class EnglishTextAnalysis(BaseTextAnalysis):
    def __init__(self):
        """Initialize the English text analysis module with the English spaCy model."""
        super().__init__("en_core_web_sm", ENGLISH_DATA)

    def calculate_readability(self, text):
        """Calculates readability for English using the Flesch-Kincaid method."""
        return textstat.flesch_kincaid_grade(text)

    def get_tooltips(self):
        """Returns tooltips in English for the analysis categories."""
        return TOOLTIP_TRANSLATIONS

nlp = None

def initialize():
    """Initializes the English text analysis module globally."""
    global nlp
    analysis = EnglishTextAnalysis()
    if analysis.initialize():
        nlp = analysis.nlp
        return True
    return False

def comprehensive_analysis(text, target_grade=8):
    """Performs a comprehensive analysis of the given text in English."""
    analysis = EnglishTextAnalysis()
    if not analysis.initialize():
        raise RuntimeError("English spaCy model not loaded.")
    return analysis.comprehensive_analysis(text, target_grade)
