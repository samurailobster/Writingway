#!/usr/bin/env python
"""
text_analysis_zh.py

Chinese-specific text analysis module inheriting from BaseTextAnalysis.
"""

import threading

import spacy
import spacy.cli
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QMessageBox

from util.base_text_analysis import BaseTextAnalysis

TOOLTIP_TRANSLATIONS = {
    "complex": """
        <b>复杂句子</b><br>
        标注出非常长或结构复杂的句子，这些句子可能难以理解。<br>
        考虑将它们分成更短、更容易理解的句子。
    """,
    "weak": """
        <b>弱表达/被动语态</b><br>
        标注出包含不精确或不果断语言的文本片段。<br>
        包括：<br>
        - 弱表达（模糊或犹豫不决的表达）<br>
        - 被动语态（主语不执行动作的句子）<br>
        例如："球被扔了"与"张三扔了球"<br>
        这两种情况都可能使文本不够直接。
    """,
    "nonstandard": """
        <b>非标准引述动词</b><br>
        指出描述说话的非典型动词<br>
        （而不是常见的如"说"）。<br>
        过于创造性的动词可能会使读者感到困惑。
    """,
    "filter": """
        <b>过滤词</b><br>
        标注出削弱表达力的词语<br>
        （如"正好"、"真的"、"简直"）。<br>
        移除它们将增强文本的清晰度。
    """,
    "telling": """
        <b>直述而非展示</b><br>
        强调直接陈述情感或行动的段落<br>
        而不是通过描述或行动来展示它们。<br>
        这可能会减少读者的投入感。
    """,
    "weak_verb": """
        <b>弱动词</b><br>
        标注没有明显情感负载的动词。<br>
        用更强烈的同义词替换它们将使文本更生动。
    """,
    "overused": """
        <b>过度使用的词语</b><br>
        指出重复过于频繁的词语。<br>
        使用同义词或改变句子结构以增加多样性。
    """,
    "pronoun": """
        <b>模糊代词引用</b><br>
        标注上下文不清的代词（"他"、"她"、"它"、"他们"）。<br>
        清晰使用代词可以防止误解。
    """,
    "repetitive": """
        <b>重复的句子开头</b><br>
        指出以相同方式开始的句子序列。<br>
        句子开头的多样性有助于保持读者的注意力。
    """
}

CHINESE_DATA = {
    "passive_deps": {"auxpass", "nsubjpass"},
    "agent_markers": {"被", "由", "让"},
    "weak_patterns": [r'可能[的地]?', r'也许[的地]?', r'大概[的地]?'],
    "weak_terms": {"可能", "也许", "大概", "或许", "好像", "似乎", "有点", "有些"},
    "standard_speech_verbs": {"说", "问"},
    "speech_verbs": {"说", "问", "喊", "叫", "回答", "回应", "告诉", "解释", "评论", "指出", "宣布", "声明", "询问", "质问"},
    "filter_words": {"看见", "听见", "感觉", "注意到", "想", "思考", "观察", "看", "听", "感受", "决定", "考虑", "似乎", "出现", "观察到", "感知", "想象"},
    "telling_verbs": {"是", "感到", "看起来", "显得", "出现", "变成"},
    "emotion_words": {"生气", "悲伤", "快乐", "兴奋", "紧张", "害怕", "担心", "尴尬", "失望", "沮丧", "恼怒", "不安", "惊恐", "高兴", "不快乐", "狂喜", "烦恼", "愤怒", "欣喜", "震惊", "惊讶", "困惑", "自豪", "满意", "满足", "热情", "嫉妒"},
    "weak_verbs": {"是", "有"},
    "common_words": {"的", "地", "得", "和", "在", "与", "从", "到", "对", "于", "但", "或", "如", "是", "有", "这", "那", "这个", "那个", "这些", "那些", "我", "你", "他", "她", "它", "我们", "你们", "他们", "她们", "它们", "不", "也", "很", "就", "都", "而", "且", "因为", "所以", "如果", "因此", "虽然", "但是", "然而"},
    "quote_pattern": r'"[^"]*"|「[^」]*」|『[^』]*』|"[^"]*"'
}

class ChineseTextAnalysis(BaseTextAnalysis, QObject):
    # Signal emitted when the model has been loaded
    model_loaded = pyqtSignal()

    def __init__(self):
        BaseTextAnalysis.__init__(self, "zh_core_web_sm", CHINESE_DATA)
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
        msgBox.setText("The model 'zh_core_web_sm' was not found. Do you want to download it?")
        msgBox.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        return msgBox.exec() == QMessageBox.StandardButton.Yes

    def download_and_load_model(self):
        """
        Downloads the spaCy model and loads it. Emits a signal when the model is loaded.
        """
        try:
            spacy.cli.download('zh_core_web_sm')
            self.nlp = spacy.load('zh_core_web_sm')
            self.model_loaded.emit()
        except Exception as e:
            print(f"Error during model download: {e}")
        finally:
            self.download_in_progress = False

    def calculate_readability(self, text):
        """
        Calculates the readability for Chinese text based on a simplified version of 
        Chinese Readability Index Explorer (CRIE) principles.
        
        This implementation focuses on:
        1. Character count (more unique characters = more complex)
        2. Average word/character length per sentence
        3. Proportion of uncommon characters
        
        A higher score indicates more difficult text (similar to other readability metrics).
        """
        # Process with spaCy to get sentences
        doc = self.nlp(text)
        sentences = list(doc.sents)

        if not sentences:
            return 0

        # Count total characters (Chinese doesn't have words in the same way as English)
        total_chars = len(text.replace(" ", "").replace("\n", ""))

        # Count sentences
        num_sentences = len(sentences)

        # Calculate average characters per sentence
        chars_per_sentence = total_chars / num_sentences if num_sentences > 0 else 0

        # Count unique characters (more unique characters indicates higher complexity)
        unique_chars = len(set(text.replace(" ", "").replace("\n", "")))

        # Create a simple metric where:
        # 1. More characters per sentence = harder to read
        # 2. Higher ratio of unique characters = harder to read (vocabulary burden)

        # Calculate unique character ratio (unique/total)
        unique_ratio = unique_chars / total_chars if total_chars > 0 else 0

        # Combine factors with appropriate weights
        # This formula is a simplified approximation inspired by CRIE principles
        readability_score = (0.5 * chars_per_sentence) + (50 * unique_ratio)

        # Scale to be roughly comparable to other readability indices (0-100 scale)
        readability_score = min(100, readability_score)

        return readability_score

    def get_tooltips(self):
        """Returns tooltips in Chinese."""
        return TOOLTIP_TRANSLATIONS

nlp = None

def initialize():
    """
    Initializes the Chinese text analysis module.
    """
    global nlp
    analysis = ChineseTextAnalysis()
    if analysis.initialize():
        nlp = analysis.nlp
        return True
    return False

def comprehensive_analysis(text, target_grade=8):
    """
    Performs a comprehensive analysis of the given text.
    """
    analysis = ChineseTextAnalysis()
    if not analysis.initialize():
        raise RuntimeError("Chinese spaCy model has not been loaded.")
    return analysis.comprehensive_analysis(text, target_grade)
