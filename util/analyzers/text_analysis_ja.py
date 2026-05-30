#!/usr/bin/env python
"""
text_analysis_ja.py

Japanese-specific text analysis module inheriting from BaseTextAnalysis.
"""

import spacy
import spacy.cli
import threading
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import QMessageBox
from util.base_text_analysis import BaseTextAnalysis
import re
import math

TOOLTIP_TRANSLATIONS = {
    "complex": """
        <b>複雑な文</b><br>
        非常に長い、または複雑な構造を持つ文を強調します。これらは理解が難しい場合があります。<br>
        より短くて簡潔な文に分割することを検討してください。
    """,
    "weak": """
        <b>弱い表現/受動態</b><br>
        曖昧さや不確実さを含む文章の部分を示します。<br>
        以下を含みます：<br>
        - 弱い表現（不明確または優柔不断な表現）<br>
        - 受動態（主語が行動を実行しない文）<br>
        例：「ボールが投げられた」vs「太郎がボールを投げた」<br>
        どちらも文章を間接的にする可能性があります。
    """,
    "nonstandard": """
        <b>非標準的な発話動詞</b><br>
        一般的な発話動詞（「言った」など）の代わりに<br>
        使用される珍しい発話動詞を示します。<br>
        あまりに創造的な動詞は読者を混乱させる可能性があります。
    """,
    "filter": """
        <b>フィルター語</b><br>
        メッセージを弱める言葉を示します<br>
        （「まさに」、「本当に」、「文字通り」など）。<br>
        これらを削除すると文章の明瞭さが向上します。
    """,
    "telling": """
        <b>説明ではなく描写</b><br>
        感情や行動が直接述べられている箇所を強調します<br>
        描写や行動を通して示す代わりに。<br>
        これは読者の関与を減少させる可能性があります。
    """,
    "weak_verb": """
        <b>弱い動詞</b><br>
        明確な感情的な力を持たない動詞を示します。<br>
        より強力な同義語に置き換えると文章が活気づきます。
    """,
    "overused": """
        <b>多用される言葉</b><br>
        頻繁に繰り返される言葉を示します。<br>
        同義語を使用するか文の構造を変えて多様性を持たせましょう。
    """,
    "pronoun": """
        <b>不明確な代名詞参照</b><br>
        文脈が不明確な代名詞（「彼」、「彼女」、「それ」、「彼ら」）を示します。<br>
        代名詞を明確に使用すると誤解を防ぐことができます。
    """,
    "repetitive": """
        <b>繰り返しの文の始まり</b><br>
        同じように始まる文の連続を示します。<br>
        文の始まり方の多様性は読者の注意を保つのに役立ちます。
    """
}

JAPANESE_DATA = {
    "passive_deps": {"aux", "nsubj"},  # Japanese passive voice dependencies
    "agent_markers": {"によって", "により"},  # Words marking the agent in passive sentences
    "weak_patterns": [r'\b\w+れる\b', r'\b\w+られる\b'],  # Patterns for potential weak expressions
    "weak_terms": {"かもしれない", "たぶん", "おそらく", "思われる", "ようだ", "みたいだ", "少し", "やや"},  # Weak/uncertain terms
    "standard_speech_verbs": {"言う", "話す", "尋ねる"},  # Standard speech verbs
    "speech_verbs": {"言う", "話す", "尋ねる", "叫ぶ", "囁く", "つぶやく", "喚く", "吠える"},  # All speech verbs including more expressive ones
    "filter_words": {"見た", "聞いた", "感じた", "気づいた", "思った", "考えた", "観察した", "見つめた", "聞き入った", "感知した", "決めた", "検討した", "現れた", "観測した", "知覚した", "想像した"},  # Words that filter experience
    "telling_verbs": {"である", "感じる", "見える", "現れる", "なる"},  # Verbs that tell rather than show
    "emotion_words": {"怒った", "悲しい", "幸せ", "興奮した", "緊張した", "恐ろしい", "心配した", "恥ずかしい", "失望した", "イライラした", "不安な", "怖い", "喜ばしい", "落ち込んだ", "不幸な", "恍惚とした", "神経質な", "激怒した", "喜んだ", "ショックを受けた", "驚いた", "混乱した", "誇らしい", "満足した", "熱心な", "嫉妬した"},  # Emotion words
    "weak_verbs": {"ある", "いる", "する"},  # Common weak verbs
    "common_words": {"は", "が", "の", "に", "と", "で", "を", "も", "や", "から", "まで", "より", "ので", "のに", "ように", "だけ", "など", "これ", "それ", "あれ", "この", "その", "あの", "ここ", "そこ", "あそこ", "私", "あなた", "彼", "彼女", "彼ら", "私たち", "あなたたち", "ない", "ある", "する", "なる", "できる"},  # Common Japanese words
    "quote_pattern": r'「[^」]*」|『[^』]*』|"[^"]*"'  # Japanese quote patterns
}

class JapaneseTextAnalysis(BaseTextAnalysis, QObject):
    # Signal emitted when the model has been loaded
    model_loaded = pyqtSignal()

    def __init__(self):
        BaseTextAnalysis.__init__(self, "ja_core_news_sm", JAPANESE_DATA)
        QObject.__init__(self)
        self.download_in_progress = False

    def initialize(self):
        """
        Initializes the spaCy model. If the model is not found, prompts the user to download it.
        """
        if super().initialize():
            return True
        if not self.download_in_progress and self.ask_for_download():
            self.download_in_progress = True
            threading.Thread(target=self.download_and_load_model, daemon=True).start()
        return False

    def ask_for_download(self):
        """
        Asks the user if they want to download the missing spaCy model.
        """
        msgBox = QMessageBox()
        msgBox.setWindowTitle("spaCy Model")
        msgBox.setText("The model 'ja_core_news_sm' was not found. Do you want to download it?")
        msgBox.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        return msgBox.exec() == QMessageBox.StandardButton.Yes

    def download_and_load_model(self):
        """
        Downloads the spaCy model and loads it. Emits a signal when the model is loaded.
        """
        try:
            spacy.cli.download('ja_core_news_sm')
            self.nlp = spacy.load('ja_core_news_sm')
            self.model_loaded.emit()
        except Exception as e:
            print(f"Error during model download: {e}")
        finally:
            self.download_in_progress = False

    def calculate_readability(self, text):
        """
        Calculates the readability for Japanese using the Obi readability score
        (a modified version suitable for Japanese text).
        
        The Obi readability formula is calculated as:
        score = 0.5 * (characters_per_sentence + 100 * complex_words_ratio)
        
        Lower scores indicate easier readability.
        """
        # Split text into sentences (Japanese sentences typically end with 。, ！, or ？)
        sentences = re.split(r'[。！？]+', text)
        sentences = [s for s in sentences if s.strip()]
        num_sentences = len(sentences)
        
        # Count characters (excluding spaces)
        num_chars = len(re.sub(r'\s', '', text))
        
        # Count kanji characters (complex characters)
        # Kanji Unicode range: U+4E00 to U+9FFF
        num_kanji = len(re.findall(r'[\u4e00-\u9fff]', text))
        
        if num_sentences == 0 or num_chars == 0:
            return 0
            
        # Calculate characters per sentence and kanji ratio
        chars_per_sentence = num_chars / num_sentences
        kanji_ratio = num_kanji / num_chars
        
        # Calculate Obi readability score (modified for Japanese)
        return 0.5 * (chars_per_sentence + 100 * kanji_ratio)
        
    def get_tooltips(self):
        """Returns tooltips in Japanese."""
        return TOOLTIP_TRANSLATIONS

nlp = None

def initialize():
    """
    Initializes the Japanese text analysis module.
    """
    global nlp
    analysis = JapaneseTextAnalysis()
    if analysis.initialize():
        nlp = analysis.nlp
        return True
    return False

def comprehensive_analysis(text, target_grade=8):
    """
    Performs a comprehensive analysis of the given text.
    """
    analysis = JapaneseTextAnalysis()
    if not analysis.initialize():
        raise RuntimeError("Japanese spaCy model has not been loaded.")
    return analysis.comprehensive_analysis(text, target_grade)