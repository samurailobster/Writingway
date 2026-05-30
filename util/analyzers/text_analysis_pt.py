#!/usr/bin/env python
"""
text_analysis_pt.py

Portuguese-specific text analysis module inheriting from BaseTextAnalysis.
"""

import spacy
import spacy.cli
import threading
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import QMessageBox
from util.base_text_analysis import BaseTextAnalysis
import re

TOOLTIP_TRANSLATIONS = {
    "complex": """
        <b>Frases complexas</b><br>
        Destaca frases muito longas ou com estrutura complicada, que podem ser difíceis de entender.<br>
        Considere dividi-las em frases mais curtas e acessíveis.
    """,
    "weak": """
        <b>Expressões fracas/voz passiva</b><br>
        Indica trechos de texto com linguagem imprecisa ou pouco assertiva.<br>
        Inclui:<br>
        - Expressões fracas (termos vagos ou indecisos)<br>
        - Voz passiva (frases onde o sujeito não realiza a ação)<br>
        Exemplo: 'A bola foi lançada' vs 'João lançou a bola'<br>
        Ambos podem tornar o texto menos direto.
    """,
    "nonstandard": """
        <b>Verbos de fala não convencionais</b><br>
        Indica verbos incomuns que descrevem a fala<br>
        (em vez dos comuns como 'disse').<br>
        Verbos muito criativos podem confundir o leitor.
    """,
    "filter": """
        <b>Palavras de filtro</b><br>
        Indica palavras que enfraquecem a mensagem<br>
        (como 'exatamente', 'realmente', 'literalmente').<br>
        Removê-las fortalecerá a clareza do texto.
    """,
    "telling": """
        <b>Contar em vez de mostrar</b><br>
        Destaca trechos onde emoções ou ações são declaradas diretamente<br>
        em vez de mostradas através de descrições ou ações.<br>
        Isso pode reduzir o envolvimento do leitor.
    """,
    "weak_verb": """
        <b>Verbos fracos</b><br>
        Indica verbos sem carga emocional clara.<br>
        Substituí-los por sinônimos mais fortes dará vida ao texto.
    """,
    "overused": """
        <b>Palavras usadas em excesso</b><br>
        Indica palavras que se repetem com muita frequência.<br>
        Use sinônimos ou mude a estrutura da frase para diversificar.
    """,
    "pronoun": """
        <b>Referências pronominais ambíguas</b><br>
        Indica pronomes ('ele', 'ela', 'isso', 'eles') com contexto pouco claro.<br>
        O uso claro de pronomes evita mal-entendidos.
    """,
    "repetitive": """
        <b>Inícios de frases repetitivos</b><br>
        Indica sequências de frases que começam da mesma forma.<br>
        A variedade nos inícios das frases mantém a atenção do leitor.
    """
}

PORTUGUESE_DATA = {
    "passive_deps": {"aux:pass", "nsubj:pass"},
    "agent_markers": {"por"},
    "weak_patterns": [r'\b\w+(?:mente)\b'],
    "weak_terms": {"talvez", "possivelmente", "provavelmente", "aparentemente", "parece", "como se", "um pouco", "ligeiramente"},
    "standard_speech_verbs": {"dizer", "perguntar"},
    "speech_verbs": {"dizer", "perguntar", "sussurrar", "gritar", "murmurar", "exclamar"},
    "filter_words": {"viu", "ouviu", "sentiu", "notou", "pensou", "perguntou-se", "observou", "olhou", "escutou", "percebeu", "decidiu", "considerou", "parecia", "apareceu", "observou", "sentiu", "percebia", "imaginou"},
    "telling_verbs": {"ser", "estar", "sentir", "parecer", "aparecer", "tornar-se"},
    "emotion_words": {"bravo", "triste", "feliz", "animado", "nervoso", "aterrorizado", "preocupado", "envergonhado", "desapontado", "frustrado", "irritado", "inquieto", "assustado", "alegre", "deprimido", "infeliz", "extasiado", "chateado", "furioso", "encantado", "chocado", "surpreso", "confuso", "orgulhoso", "satisfeito", "contente", "entusiasmado", "ciumento"},
    "weak_verbs": {"ser", "estar"},
    "common_words": {"e", "em", "no", "na", "de", "do", "da", "a", "o", "mas", "ou", "como", "é", "são", "foi", "era", "tem", "têm", "isso", "desse", "esse", "essa", "este", "esta", "lá", "aqui", "meu", "seu", "dele", "dela", "nosso", "seu", "deles", "se", "não", "sim", "que", "porque", "quando", "se", "pois", "qual", "quem", "onde"},
    "quote_pattern": r'"[^"]*"|\'[^\']*\''
}

class PortugueseTextAnalysis(BaseTextAnalysis, QObject):
    # Signal emitted when the model has been loaded
    model_loaded = pyqtSignal()

    def __init__(self):
        BaseTextAnalysis.__init__(self, "pt_core_news_sm", PORTUGUESE_DATA)
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
        msgBox.setText("The model 'pt_core_news_sm' was not found. Do you want to download it?")
        msgBox.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        return msgBox.exec() == QMessageBox.StandardButton.Yes

    def download_and_load_model(self):
        """
        Downloads the spaCy model and loads it. Emits a signal when the model is loaded.
        """
        try:
            spacy.cli.download('pt_core_news_sm')
            self.nlp = spacy.load('pt_core_news_sm')
            self.model_loaded.emit()
        except Exception as e:
            print(f"Error during model download: {e}")
        finally:
            self.download_in_progress = False

    def calculate_readability(self, text):
        """
        Calculates the readability for Portuguese using the Adapted Flesch Index (Índice de Legibilidade Flesch).
        
        The formula is: 206.835 - (1.015 * ASL) - (84.6 * ASW)
        Where:
        - ASL = Average Sentence Length
        - ASW = Average number of syllables per word
        
        The result interpretation is:
        Score          Level
        90-100         Very easy
        80-90          Easy
        70-80          Fairly easy
        60-70          Standard
        50-60          Fairly difficult
        30-50          Difficult
        0-30           Very difficult
        """
        words = text.split()
        num_words = len(words)
        sentences = re.split(r'[.!?]+', text)
        sentences = [s for s in sentences if s.strip()]
        num_sentences = len(sentences)
        
        if num_sentences == 0 or num_words == 0:
            return 0
        
        # Calculate average sentence length
        asl = num_words / num_sentences
        
        # Count syllables (approximation for Portuguese)
        def count_syllables(word):
            word = word.lower()
            # Count vowel groups as syllables
            vowels = "aeiouáàâãéèêíìóòôõúù"
            count = 0
            in_vowel_group = False
            
            for char in word:
                if char in vowels:
                    if not in_vowel_group:
                        count += 1
                        in_vowel_group = True
                else:
                    in_vowel_group = False
            
            # Handle special cases for Portuguese
            # If word ends with 'r', 'l', 'm', 'z' and has more than one syllable, reduce by one
            if len(word) > 2 and word[-1] in 'rlmz' and count > 1:
                count -= 1
            
            # Ensure at least one syllable
            return max(1, count)
        
        total_syllables = sum(count_syllables(word) for word in words)
        asw = total_syllables / num_words
        
        # Calculate Flesch Index adapted for Portuguese
        flesch_index = 206.835 - (1.015 * asl) - (84.6 * asw)
        
        # Ensure index is within bounds
        return max(0, min(100, flesch_index))
        
    def get_tooltips(self):
        """Returns tooltips in Portuguese."""
        return TOOLTIP_TRANSLATIONS

nlp = None

def initialize():
    """
    Initializes the Portuguese text analysis module.
    """
    global nlp
    analysis = PortugueseTextAnalysis()
    if analysis.initialize():
        nlp = analysis.nlp
        return True
    return False

def comprehensive_analysis(text, target_grade=8):
    """
    Performs a comprehensive analysis of the given text.
    """
    analysis = PortugueseTextAnalysis()
    if not analysis.initialize():
        raise RuntimeError("Portuguese spaCy model has not been loaded.")
    return analysis.comprehensive_analysis(text, target_grade)