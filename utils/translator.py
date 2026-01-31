from deep_translator import GoogleTranslator
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException


def translate_reason(text: str):
    try:
        lang = detect(text)
    except LangDetectException:
        lang = "en"

    if lang == "pt":
        pt = text
        en = GoogleTranslator(source="pt", target="en").translate(text)
    else:
        en = text
        pt = GoogleTranslator(source="en", target="pt").translate(text)

    return pt, en
