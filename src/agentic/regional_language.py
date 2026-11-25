"""
src/agentic/regional_language.py — Agent 4: Regional Language Intelligence Agent.

Objective:
Improve authentication usability for Indian regional-language speakers:
- Target languages: English (en), Hindi (hi), Tamil (ta), Kannada (kn), Telugu (te), Gujarati (gu).
- Automatic language identification & confidence estimation.
- Multilingual recovery message templates.
- Strict security constraints:
  - Do NOT claim that translation improves biometric accuracy.
  - Do NOT claim language-specific accuracy without actual benchmark results.
  - Unknown or insufficiently validated languages are routed with fail-safe recovery prompts.
"""

from __future__ import annotations

import time
import math
from typing import Dict, Any, Optional, List, Union
import numpy as np

from src.agentic.schemas import StandardAgentResponse, AgentStatus, RegionalLanguage


# Multilingual localized recovery message templates
LOCALIZED_PROMPTS: Dict[str, Dict[str, str]] = {
    "en": {
        "COLLECT_ADDITIONAL_SPEECH": "Please speak a few more words clearly so we can confirm your voice.",
        "REQUEST_QUIETER_ENVIRONMENT": "There is noticeable background noise. Please move to a quieter space and speak again.",
        "SPEAK_CLOSER_TO_MIC": "Your voice sounded faint. Please move closer to the microphone and repeat.",
        "REDUCE_MICROPHONE_GAIN": "Your microphone audio was too loud or distorted. Please lower your microphone volume.",
        "REQUEST_FRESH_RECORDING": "We could not verify your audio. Please record a fresh sample.",
        "STEP_UP_CHALLENGE": "Additional verification required. Please complete secondary confirmation.",
    },
    "hi": {
        "COLLECT_ADDITIONAL_SPEECH": "कृपया स्पष्ट रूप से कुछ और शब्द बोलें ताकि हम आपकी आवाज़ सत्यापित कर सकें।",
        "REQUEST_QUIETER_ENVIRONMENT": "पृष्ठभूमि में अत्यधिक शोर है। कृपया किसी शांत स्थान पर जाकर पुनः बोलें।",
        "SPEAK_CLOSER_TO_MIC": "आपकी आवाज़ धीमी थी। कृपया माइक्रोफ़ोन के करीब आकर पुनः बोलें।",
        "REDUCE_MICROPHONE_GAIN": "आवाज़ में विकृति है। कृपया माइक्रोफ़ोन की आवाज़ कम करें।",
        "REQUEST_FRESH_RECORDING": "ऑडियो सत्यापित नहीं हो सका। कृपया नया रिकॉर्डिंग भेजें।",
        "STEP_UP_CHALLENGE": "अतिरिक्त सत्यापन आवश्यक है। कृपया अगली पुष्टि पूरी करें।",
    },
    "ta": {
        "COLLECT_ADDITIONAL_SPEECH": "உங்கள் குரலை உறுதிப்படுத்த மேலும் சில வார்த்தைகளை தெளிவாகப் பேசுங்கள்.",
        "REQUEST_QUIETER_ENVIRONMENT": "பின்னணி இரைச்சல் அதிகமாக உள்ளது. தயவுசெய்து அமைதியான இடத்திற்குச் சென்று மீண்டும் பேசவும்.",
        "SPEAK_CLOSER_TO_MIC": "உங்கள் குரல் மெதுவாக உள்ளது. மைக்ரோஃபோனுக்கு அருகில் வந்து பேசவும்.",
        "REDUCE_MICROPHONE_GAIN": "ஒலி சிதைந்துள்ளது. மைக்ரோஃபோன் அளவைக் குறைக்கவும்.",
        "REQUEST_FRESH_RECORDING": "பதிவை உறுதிப்படுத்த முடியவில்லை. தயவுசெய்து மீண்டும் பதிவு செய்யவும்.",
        "STEP_UP_CHALLENGE": "கூடுதல் சரிபார்ப்பு தேவைப்படுகிறது.",
    },
    "kn": {
        "COLLECT_ADDITIONAL_SPEECH": "ನಿಮ್ಮ ಧ್ವನಿಯನ್ನು ಪರಿಶೀಲಿಸಲು ದಯವಿಟ್ಟು ಇನ್ನೂ ಕೆಲವು ಪದಗಳನ್ನು ಸ್ಪಷ್ಟವಾಗಿ ಮಾತನಾಡಿ.",
        "REQUEST_QUIETER_ENVIRONMENT": "ಹಿನ್ನೆಲೆ ಶಬ್ದ ಹೆಚ್ಚಾಗಿದೆ. ದಯವಿಟ್ಟು ಶಾಂತವಾದ ಸ್ಥಳಕ್ಕೆ ತೆರಳಿ ಮತ್ತೆ ಮಾತನಾಡಿ.",
        "SPEAK_CLOSER_TO_MIC": "ನಿಮ್ಮ ಧ್ವನಿ ಕಡಿಮೆಯಾಗಿದೆ. ಮೈಕ್ರೊಫೋನ್‌ಗೆ ಹತ್ತಿರವಾಗಿ ಮಾತನಾಡಿ.",
        "REDUCE_MICROPHONE_GAIN": "ಧ್ವನಿಯಲ್ಲಿ ಅಡಚಣೆ ಇದೆ. ಮೈಕ್ರೊಫೋನ್ ಧ್ವನಿಯನ್ನು ಕಡಿಮೆ ಮಾಡಿ.",
        "REQUEST_FRESH_RECORDING": "ಧ್ವನಿಯನ್ನು ಪರಿಶೀಲಿಸಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ. ದಯವಿಟ್ಟು ಹೊಸ ರೆಕಾರ್ಡಿಂಗ್ ಮಾಡಿ.",
        "STEP_UP_CHALLENGE": "ಹೆಚ್ಚುವರಿ ಪರಿಶೀಲನೆ ಅಗತ್ಯವಿದೆ.",
    },
    "te": {
        "COLLECT_ADDITIONAL_SPEECH": "మీ స్వరాన్ని ధృవీకరించడానికి దయచేసి మరికొన్ని పదాలు స్పష్టంగా మాట్లాడండి.",
        "REQUEST_QUIETER_ENVIRONMENT": "నేపథ్య శబ్దం ఎక్కువగా ఉంది. దయచేసి ప్రశాంతమైన ప్రదేశంలో మాట్లాడండి.",
        "SPEAK_CLOSER_TO_MIC": "మీ స్వరం తక్కువగా ఉంది. మైక్రోఫోన్‌కు దగ్గరగా మాట్లాడండి.",
        "REDUCE_MICROPHONE_GAIN": "ధ్వనిలో అవాంతరాలు ఉన్నాయి. మైక్రోఫోన్ వాల్యూమ్ తగ్గించండి.",
        "REQUEST_FRESH_RECORDING": "ఆడియో ధృవీకరించబడలేదు. దయచేసి కొత్త రికార్డింగ్ చేయండి.",
        "STEP_UP_CHALLENGE": "అదనపు ధృవీకరణ అవసరం.",
    },
    "gu": {
        "COLLECT_ADDITIONAL_SPEECH": "તમારો અવાજ ચકાસવા માટે કૃપા કરીને થોડા વધુ શબ્દો સ્પષ્ટ બોલો.",
        "REQUEST_QUIETER_ENVIRONMENT": "પાછળ ઘણો અવાજ છે. કૃપા કરીને શાંત જગ્યાએ જઈને ફરીથી બોલો.",
        "SPEAK_CLOSER_TO_MIC": "તમારો અવાજ ધીમો હતો. કૃપા કરીને માઇક્રોફોનની નજીક આવીને બોલો.",
        "REDUCE_MICROPHONE_GAIN": "અવાજ વિકૃત છે. કૃપા કરીને માઇક્રોફોન અવાજ ઓછો કરો.",
        "REQUEST_FRESH_RECORDING": "રેકોર્ડિંગ ચકાસી શકાયું નથી. કૃપા કરીને નવું રેકોર્ડિંગ આપો.",
        "STEP_UP_CHALLENGE": "વધારાની ચકાસણી જરૂરી છે.",
    },
}


# Lightweight transcript keyword heuristics (non-authoritative; documented limitation).
# Full ASR-based detection would use Faster Whisper — kept optional in a future phase.
_TRANSCRIPT_KEYWORDS: Dict[str, List[str]] = {
    "hi": ["है", "कृपया", "मुझे", "कृपा", "धन्यवाद", "अभी", "कौन", "समय"],
    "ta": ["உங்கள்", "தயவுசெய்து", "குரல்", "அவர்கள்", "அன்பு", "அவர்", "நீங்கள்"],
    "kn": ["ನಿಮ್ಮ", "ದಯವಿಟ್ಟು", "ಧ್வನಿ", "ಕೊನೆಯ", "ನಿಮಗೆ"],
    "te": ["మీ", "దయచేసి", "స్వరం", "ప్రశాంత", "మీకు"],
    "gu": ["તમારો", "કૃપા", "અવાજ", "શાંત"],
}


class RegionalLanguageAgent:
    """Agent 4: Identifies regional Indian languages and generates native-language recovery directives."""

    AGENT_NAME = "regional_language_agent"
    SUPPORTED_LANGUAGES = {"en", "hi", "ta", "kn", "te", "gu"}

    def __init__(self):
        pass

    @staticmethod
    def _heuristic_language_detect(transcript_text: Optional[str]) -> Optional[str]:
        """Very small keyword heuristic for transcript-only language hints (non-authoritative)."""
        if not transcript_text:
            return None
        text = transcript_text.lower()
        best, best_score = None, 0
        for lang, keywords in _TRANSCRIPT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in text)
            if score > best_score:
                best, best_score = lang, score
        return best

    def identify_language(
        self,
        session_id: str,
        hint_language: Optional[str] = None,
        transcript_text: Optional[str] = None,
        detected_language: Optional[str] = None,
        confidence: Optional[float] = None,
    ) -> StandardAgentResponse:
        t0 = time.perf_counter()
        limitations: List[str] = [
            "Language identification does not substitute speaker embeddings or affect verification accuracy.",
            "Unsupported languages default to graceful fallback with English/Hindi localized prompts.",
        ]

        target_lang = (
            detected_language
            or hint_language
            or self._heuristic_language_detect(transcript_text)
            or "en"
        ).lower().strip()
        lang_conf = confidence if confidence is not None else (0.90 if target_lang in self.SUPPORTED_LANGUAGES else 0.40)

        # Validate language support
        is_supported = target_lang in self.SUPPORTED_LANGUAGES
        resolved_lang = target_lang if is_supported else "unknown"
        preferred_recovery_lang = resolved_lang if is_supported else "en"

        status = AgentStatus.PASS if is_supported else AgentStatus.WARNING
        rec_action = "PROCEED" if is_supported else "CONFIRM_PREFERRED_LANGUAGE"

        findings: Dict[str, Any] = {
            "detected_language": resolved_lang,
            "is_supported_regional_language": is_supported,
            "preferred_recovery_language": preferred_recovery_lang,
            "available_translations": list(self.SUPPORTED_LANGUAGES),
            "summary": (
                f"Identified regional language: {resolved_lang} (confidence: {lang_conf:.2f})."
                if is_supported
                else f"Language '{target_lang}' is outside primary regional validation profiles. Fallback to English."
            ),
        }

        measurements: Dict[str, Optional[float]] = {
            "language_confidence": lang_conf,
            "target_language_supported": 1.0 if is_supported else 0.0,
        }

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return StandardAgentResponse(
            agent_name=self.AGENT_NAME,
            session_id=session_id,
            status=status,
            findings=findings,
            measurements=measurements,
            confidence=lang_conf,
            limitations=limitations,
            recommended_action=rec_action,
            processing_time_ms=elapsed_ms,
            error=None,
        )

    def get_localized_message(self, action_key: str, lang: str = "en") -> str:
        """Helper to retrieve localized recovery text for a recommended action."""
        lang_key = lang.lower() if lang.lower() in LOCALIZED_PROMPTS else "en"
        return LOCALIZED_PROMPTS[lang_key].get(
            action_key,
            LOCALIZED_PROMPTS["en"].get(action_key, "Please provide another clear voice sample."),
        )
