import logging
import platform
import subprocess
import threading

import pyttsx3

from settings.settings_manager import WWSettingsManager

# Configure logging
# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class TTSManager:
    def __init__(self):
        self._engine = None
        self._thread = None
        self.is_mac = platform.system() == "Darwin"
        logging.debug("TTSManager initialized")

    def get_tts_rate(self):
        """
        Read the settings.json file and return the desired TTS rate.
        We'll use 200 as the normal rate and 300 for fast speech.
        """
        normal_rate = 200  # Updated normal rate (default speed)
        fast_rate = 300    # Fast speech remains the same
        rate = normal_rate

        if WWSettingsManager.get_setting("general", "fast_tts"):
            rate = fast_rate

        logging.debug(f"TTS rate set to {rate}")
        return rate

    def get_engine(self):
        """
        Create and return a new pyttsx3 engine instance with the proper rate set.
        """
        engine = pyttsx3.init()
        engine.setProperty("rate", self.get_tts_rate())
        logging.debug("TTS engine created and rate set")
        return engine

    def speak(self, text, start_position=0, on_complete=None):
        """
        Speak the text starting from the given cursor location.
        On macOS, use the 'say' command. On other OS, use pyttsx3.
        Optionally, call on_complete() when done to update the TTS button (or any other UI element) back from "stop".
        """
        def run_tts():
            if self.is_mac:
                logging.debug("Using macOS 'say' command")
                text_to_speak = text[start_position:]
                rate = self.get_tts_rate()
                logging.debug(f"Speaking text: {text_to_speak} at rate: {rate}")
                subprocess.run(["say", "-r", str(rate), text_to_speak])
                logging.debug("macOS 'say' command finished")
            else:
                logging.debug("Using pyttsx3 TTS engine")
                self._engine = self.get_engine()
                # Start speaking from the provided cursor location (start_position)
                text_to_speak = text[start_position:]
                logging.debug(f"Speaking text: {text_to_speak}")
                self._engine.say(text_to_speak)
                self._engine.runAndWait()
                logging.debug("pyttsx3 TTS engine finished speaking")
                self._engine = None
                logging.debug("TTS engine set to None")

            # Invoke the on_complete callback if provided
            if on_complete is not None:
                on_complete()

        # Run the TTS in a separate thread
        self._thread = threading.Thread(target=run_tts)
        self._thread.start()
        logging.debug("TTS thread started")

    def stop(self):
        """
        Stop the current speech (if any) and reset the engine.
        """
        if self.is_mac:
            logging.debug("Stopping macOS 'say' command")
            subprocess.run(["killall", "say"])
        else:
            if self._engine is not None:
                logging.debug("Stopping pyttsx3 TTS engine")
                self._engine.stop()
                self._engine = None
            if self._thread is not None:
                logging.debug("Joining TTS thread")
                self._thread.join()
                self._thread = None
        logging.debug("TTS engine and thread stopped")

WW_TTSManager = TTSManager()

# Usage example
if __name__ == "__main__":
    WW_TTSManager.speak("Hello, this is a test.")
