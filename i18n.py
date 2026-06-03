import json
import os
import streamlit as st


LOCALE_DIR = os.path.join(os.path.dirname(__file__), "locales")
SUPPORTED_LANGUAGES = {"de": "Deutsch", "en": "English", "pl": "Polski"}
_translations: dict[str, dict[str, str]] = {}


def _load_lang(lang: str) -> dict[str, str]:
    path = os.path.join(LOCALE_DIR, f"{lang}.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def get_translations(lang: str) -> dict[str, str]:
    if lang not in _translations:
        _translations[lang] = _load_lang(lang)
    return _translations[lang]


def _(key: str, **kwargs) -> str:
    lang = st.session_state.get("language", "de")
    trans = get_translations(lang)
    text = trans.get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text


def render_language_selector():
    current = st.session_state.get("language", "de")
    label = _("label.language")
    selected = st.selectbox(
        label,
        options=list(SUPPORTED_LANGUAGES.keys()),
        format_func=lambda k: SUPPORTED_LANGUAGES.get(k, k),
        index=list(SUPPORTED_LANGUAGES.keys()).index(current) if current in SUPPORTED_LANGUAGES else 0,
        key="language_selector",
    )
    if selected != current:
        st.session_state.language = selected
        st.rerun()
