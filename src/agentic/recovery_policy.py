"""
src/agentic/recovery_policy.py — Deterministic recovery policy (Phase 3).

Gemini may only *select* one of the approved actions below and phrase a short
customer message. Security-relevant decisions stay deterministic:
- Gemini can never change the outcome (VERIFIED / RECOVERY_REQUIRED / BLOCKED).
- Gemini can never downgrade identity/security recovery to an audio-only retry.
- Messages are validated for secret requests and false verification claims.
- Template fallbacks exist for every action in every supported language.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

APPROVED_ACTIONS = (
    "COLLECT_MORE_SPEECH",
    "RETRY_RECORDING",
    "IMPROVE_AUDIO_ENVIRONMENT",
    "RETRY_UPLOAD",
    "CONTINUE_IN_PREFERRED_LANGUAGE",
    "INDEPENDENT_VERIFICATION",
    "HUMAN_REVIEW",
)

SUPPORTED_LANGUAGES = ("en", "hi", "ta", "kn", "te", "gu")
LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "ta": "Tamil",
    "kn": "Kannada",
    "te": "Telugu",
    "gu": "Gujarati",
}

# Actions that must never be replaced by a weaker audio-only retry.
SECURITY_SENSITIVE_ACTIONS = {"INDEPENDENT_VERIFICATION", "HUMAN_REVIEW"}

_IDENTITY_REASONS = {
    "SPEAKER_IDENTITY_MISMATCH",
    "CONFLICTING_EVIDENCE",
    "LOW_CONFIDENCE_EVIDENCE",
    "MISSING_OR_UNAVAILABLE_EVIDENCE",
    "INVALID_EVIDENCE_PAYLOAD",
    "CROSS_SESSION_EVIDENCE_REJECTED",
    "STALE_EVIDENCE_REJECTED",
    "AUDIO_RETRY_LIMIT_EXCEEDED",
    "SERVICE_RETRY_LIMIT_EXCEEDED",
    "CREDIBLE_DEEPFAKE_DETECTED",
    "SESSION_LOCKED_SUSPICIOUS",
    "MOCK_EVIDENCE_REJECTED_IN_PROD",
}

_SECRET_REQUEST_RE = re.compile(
    r"(pass\s*word|passcode|\bpin\b|\botp\b|one[-\s]?time\s*(code|password)|"
    r"card\s*number|\bcvv\b|\bcvc\b|secret\s*(code|key)|credential|"
    r"पासवर्ड|पिन|ओटीपी|गोपनीय|"
    r"கடவுச்சொல்|ரகசிய|"
    r"ಪಾಸ್‌ವರ್ಡ್|ರಹಸ್ಯ|"
    r"పాస్‌వర్డ్|రహస్య|"
    r"પાસવર્ડ|ગુપ્ત)",
    re.IGNORECASE,
)

_FALSE_VERIFICATION_RE = re.compile(
    r"(successfully\s+verified|verification\s+(is\s+)?(successful|complete)|"
    r"you\s+are\s+verified|identity\s+confirmed|\b(are|is)\s+verified\b|"
    r"सत्यापित\s+हो\s+गया|सत्यापन\s+सफल|"
    r"சரிபார்க்கப்பட்டது|"
    r"ಪರಿಶೀಲಿಸಲಾಗಿದೆ|"
    r"ధృవీకరించబడింది|"
    r"ચકાસાયેલ)",
    re.IGNORECASE,
)

_SCRIPT_RANGES = {
    "hi": ("\u0900", "\u097f"),
    "ta": ("\u0b80", "\u0bff"),
    "kn": ("\u0c80", "\u0cff"),
    "te": ("\u0c00", "\u0c7f"),
    "gu": ("\u0a80", "\u0aff"),
}

TEMPLATES: Dict[str, Dict[str, str]] = {
    "en": {
        "COLLECT_MORE_SPEECH": "Please speak a few more words clearly so we can confirm your voice.",
        "RETRY_RECORDING": "We could not hear a clear recording. Please record your voice again in one quiet take.",
        "IMPROVE_AUDIO_ENVIRONMENT": "There is too much background noise. Please move somewhere quieter and try again.",
        "RETRY_UPLOAD": "Your recording did not upload completely. Please check your connection and send it again.",
        "CONTINUE_IN_PREFERRED_LANGUAGE": "You can continue in your preferred language. Please speak clearly in the same language.",
        "INDEPENDENT_VERIFICATION": "We could not confirm your voice with certainty. Please complete verification using your registered backup method.",
        "HUMAN_REVIEW": "We could not complete voice verification. Please contact customer support for a secure review.",
    },
    "hi": {
        "COLLECT_MORE_SPEECH": "कृपया कुछ और शब्द स्पष्ट रूप से बोलें ताकि हम आपकी आवाज़ की पुष्टि कर सकें।",
        "RETRY_RECORDING": "हमें स्पष्ट रिकॉर्डिंग नहीं मिली। कृपया शांत वातावरण में अपनी आवाज़ फिर से रिकॉर्ड करें।",
        "IMPROVE_AUDIO_ENVIRONMENT": "पृष्ठभूमि में बहुत शोर है। कृपया किसी शांत स्थान पर जाकर फिर से प्रयास करें।",
        "RETRY_UPLOAD": "आपकी रिकॉर्डिंग पूरी तरह अपलोड नहीं हुई। कृपया कनेक्शन जाँचकर दोबारा भेजें।",
        "CONTINUE_IN_PREFERRED_LANGUAGE": "आप अपनी पसंदीदा भाषा में जारी रख सकते हैं। कृपया उसी भाषा में स्पष्ट बोलें।",
        "INDEPENDENT_VERIFICATION": "हम आपकी आवाज़ की पुष्टि निश्चित रूप से नहीं कर सके। कृपया अपनी पंजीकृत बैकअप विधि से सत्यापन पूरा करें।",
        "HUMAN_REVIEW": "हम आवाज़ सत्यापन पूरा नहीं कर सके। कृपया सुरक्षित समीक्षा के लिए ग्राहक सहायता से संपर्क करें।",
    },
    "ta": {
        "COLLECT_MORE_SPEECH": "உங்கள் குரலை உறுதிப்படுத்த மேலும் சில வார்த்தைகளை தெளிவாகப் பேசுங்கள்.",
        "RETRY_RECORDING": "தெளிவான பதிவு கிடைக்கவில்லை. அமைதியான இடத்தில் மீண்டும் பதிவு செய்யுங்கள்.",
        "IMPROVE_AUDIO_ENVIRONMENT": "பின்னணி இரைச்சல் அதிகம். அமைதியான இடத்திற்குச் சென்று மீண்டும் முயற்சிக்கவும்.",
        "RETRY_UPLOAD": "பதிவு முழுமையாக பதிவேற்றப்படவில்லை. இணைப்பைச் சரிபார்த்து மீண்டும் அனுப்பவும்.",
        "CONTINUE_IN_PREFERRED_LANGUAGE": "உங்கள் விருப்ப மொழியில் தொடரலாம். அதே மொழியில் தெளிவாகப் பேசுங்கள்.",
        "INDEPENDENT_VERIFICATION": "உங்கள் குரலை உறுதியாகச் சரிபார்க்க முடியவில்லை. பதிவு செய்த மாற்று முறையில் சரிபார்ப்பை முடிக்கவும்.",
        "HUMAN_REVIEW": "குரல் சரிபார்ப்பை முடிக்க முடியவில்லை. பாதுகாப்பான மதிப்பாய்வுக்கு வாடிக்கையாளர் ஆதரவைத் தொடர்பு கொள்ளவும்.",
    },
    "kn": {
        "COLLECT_MORE_SPEECH": "ನಿಮ್ಮ ಧ್ವನಿಯನ್ನು ಖಚಿತಪಡಿಸಲು ಇನ್ನೂ ಕೆಲವು ಪದಗಳನ್ನು ಸ್ಪಷ್ಟವಾಗಿ ಮಾತನಾಡಿ.",
        "RETRY_RECORDING": "ಸ್ಪಷ್ಟ ರೆಕಾರ್ಡಿಂಗ್ ಸಿಗಲಿಲ್ಲ. ಶಾಂತ ಸ್ಥಳದಲ್ಲಿ ಮತ್ತೆ ರೆಕಾರ್ಡ್ ಮಾಡಿ.",
        "IMPROVE_AUDIO_ENVIRONMENT": "ಹಿನ್ನೆಲೆ ಶಬ್ದ ಹೆಚ್ಚಿದೆ. ಶಾಂತ ಸ್ಥಳಕ್ಕೆ ತೆರಳಿ ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.",
        "RETRY_UPLOAD": "ನಿಮ್ಮ ರೆಕಾರ್ಡಿಂಗ್ ಪೂರ್ಣವಾಗಿ ಅಪ್ಲೋಡ್ ಆಗಿಲ್ಲ. ಸಂಪರ್ಕ ಪರಿಶೀಲಿಸಿ ಮತ್ತೆ ಕಳುಹಿಸಿ.",
        "CONTINUE_IN_PREFERRED_LANGUAGE": "ನಿಮ್ಮ ಇಷ್ಟದ ಭಾಷೆಯಲ್ಲಿ ಮುಂದುವರಿಸಬಹುದು. ಅದೇ ಭಾಷೆಯಲ್ಲಿ ಸ್ಪಷ್ಟವಾಗಿ ಮಾತನಾಡಿ.",
        "INDEPENDENT_VERIFICATION": "ನಿಮ್ಮ ಧ್ವನಿಯನ್ನು ಖಚಿತವಾಗಿ ಪರಿಶೀಲಿಸಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ. ನೋಂದಾಯಿತ ಬ್ಯಾಕಪ್ ವಿಧಾನದಿಂದ ಪರಿಶೀಲನೆ ಪೂರ್ಣಗೊಳಿಸಿ.",
        "HUMAN_REVIEW": "ಧ್ವನಿ ಪರಿಶೀಲನೆ ಪೂರ್ಣಗೊಳ್ಳಲಿಲ್ಲ. ಸುರಕ್ಷಿತ ಪರಿಶೀಲನೆಗಾಗಿ ಗ್ರಾಹಕ ಬೆಂಬಲವನ್ನು ಸಂಪರ್ಕಿಸಿ.",
    },
    "te": {
        "COLLECT_MORE_SPEECH": "మీ స్వరాన్ని నిర్ధారించడానికి మరికొన్ని పదాలు స్పష్టంగా మాట్లాడండి.",
        "RETRY_RECORDING": "స్పష్టమైన రికార్డింగ్ లభించలేదు. ప్రశాంతమైన ప్రదేశంలో మళ్లీ రికార్డ్ చేయండి.",
        "IMPROVE_AUDIO_ENVIRONMENT": "నేపథ్య శబ్దం ఎక్కువగా ఉంది. ప్రశాంతమైన ప్రదేశానికి వెళ్లి మళ్లీ ప్రయత్నించండి.",
        "RETRY_UPLOAD": "మీ రికార్డింగ్ పూర్తిగా అప్‌లోడ్ కాలేదు. కనెక్షన్ తనిఖీ చేసి మళ్లీ పంపండి.",
        "CONTINUE_IN_PREFERRED_LANGUAGE": "మీకు ఇష్టమైన భాషలో కొనసాగవచ్చు. అదే భాషలో స్పష్టంగా మాట్లాడండి.",
        "INDEPENDENT_VERIFICATION": "మీ స్వరాన్ని ఖచ్చితంగా ధృవీకరించలేకపోయాము. నమోదిత బ్యాకప్ పద్ధతిలో ధృవీకరణ పూర్తి చేయండి.",
        "HUMAN_REVIEW": "స్వర ధృవీకరణ పూర్తికాలేదు. సురక్షిత సమీక్ష కోసం కస్టమర్ సపోర్ట్‌ను సంప్రదించండి.",
    },
    "gu": {
        "COLLECT_MORE_SPEECH": "તમારો અવાજ ખાતરી કરવા માટે થોડા વધુ શબ્દો સ્પષ્ટ બોલો.",
        "RETRY_RECORDING": "સ્પષ્ટ રેકોર્ડિંગ મળ્યું નથી. શાંત જગ્યાએ ફરીથી રેકોર્ડ કરો.",
        "IMPROVE_AUDIO_ENVIRONMENT": "પાછળ ઘણો અવાજ છે. શાંત જગ્યાએ જઈને ફરી પ્રયાસ કરો.",
        "RETRY_UPLOAD": "તમારું રેકોર્ડિંગ પૂર્ણ અપલોડ થયું નથી. કનેક્શન તપાસીને ફરી મોકલો.",
        "CONTINUE_IN_PREFERRED_LANGUAGE": "તમે તમારી પસંદગીની ભાષામાં ચાલુ રાખી શકો છો. એ જ ભાષામાં સ્પષ્ટ બોલો.",
        "INDEPENDENT_VERIFICATION": "અમે તમારો અવાજ ચોક્કસ ચકાસી શક્યા નથી. નોંધાયેલ બેકઅપ પદ્ધતિથી ચકાસણી પૂર્ણ કરો.",
        "HUMAN_REVIEW": "અવાજ ચકાસણી પૂર્ણ થઈ શકી નથી. સુરક્ષિત સમીક્ષા માટે ગ્રાહક સહાયનો સંપર્ક કરો.",
    },
}


def normalize_language(value: Optional[str]) -> str:
    if not value:
        return "en"
    text = str(value).strip().lower()
    aliases = {
        "english": "en", "hindi": "hi", "tamil": "ta", "kannada": "kn",
        "telugu": "te", "gujarati": "gu", "unknown": "en", "": "en",
    }
    text = aliases.get(text, text)
    return text if text in SUPPORTED_LANGUAGES else "en"


def template_message(action: str, language: Optional[str]) -> str:
    lang = normalize_language(language)
    return TEMPLATES[lang].get(action) or TEMPLATES["en"].get(action, "Please provide another clear voice sample.")


def derive_outcome(
    verification_status: Optional[str],
    decision: Optional[str],
    session_state: Optional[str],
    reason_codes: Optional[Iterable[str]] = None,
) -> str:
    """Map trust-engine facts to the three Phase 3 outcomes deterministically."""
    status = (verification_status or "").upper()
    decision_value = (decision or "").upper()
    state = (session_state or "").upper()
    reasons = {str(r).upper() for r in (reason_codes or [])}

    if status == "SUSPICIOUS" or state == "BLOCKED":
        return "BLOCKED"
    if "CREDIBLE_DEEPFAKE_DETECTED" in reasons or "SESSION_LOCKED_SUSPICIOUS" in reasons:
        return "BLOCKED"
    if decision_value == "DENY" and status != "INCONCLUSIVE":
        return "BLOCKED"
    if status == "VERIFIED" and decision_value == "ALLOW":
        return "VERIFIED"
    return "RECOVERY_REQUIRED"


def _agent_status(agent_findings: Optional[Dict[str, Any]], key: str) -> str:
    if not isinstance(agent_findings, dict):
        return ""
    payload = agent_findings.get(key)
    if not isinstance(payload, dict):
        return ""
    return str(payload.get("status") or "").upper()


def _agent_recommended(agent_findings: Optional[Dict[str, Any]], key: str) -> str:
    if not isinstance(agent_findings, dict):
        return ""
    payload = agent_findings.get(key)
    if not isinstance(payload, dict):
        return ""
    return str(payload.get("recommended_action") or "").upper()


def derive_action(
    *,
    outcome: str,
    recovery_action: Optional[str],
    reason_codes: Optional[Iterable[str]],
    agent_findings: Optional[Dict[str, Any]],
) -> Optional[str]:
    """Deterministic action selection. Never returns a non-approved action."""
    if outcome == "VERIFIED":
        return None
    if outcome == "BLOCKED":
        return "HUMAN_REVIEW"

    reasons = {str(r).upper() for r in (reason_codes or [])}
    legacy = (recovery_action or "").upper()

    # Identity / security evidence issues take precedence over audio retries.
    if reasons & _IDENTITY_REASONS:
        return "INDEPENDENT_VERIFICATION"
    if legacy in ("REQUIRE_INDEPENDENT_AUTHENTICATION", "ESCALATE_FOR_MANUAL_REVIEW"):
        return "INDEPENDENT_VERIFICATION" if legacy == "REQUIRE_INDEPENDENT_AUTHENTICATION" else "HUMAN_REVIEW"

    network_status = _agent_status(agent_findings, "network_resilience")
    network_action = _agent_recommended(agent_findings, "network_resilience")
    if network_status == "ERROR" or "UPLOAD" in network_action or "RETRY" in network_action:
        return "RETRY_UPLOAD"

    speech_status = _agent_status(agent_findings, "speech_sufficiency")
    speech_action = _agent_recommended(agent_findings, "speech_sufficiency")
    if speech_status in ("WARNING", "INCONCLUSIVE") or "SPEECH" in speech_action or "LONGER" in speech_action:
        return "COLLECT_MORE_SPEECH"

    acoustic_action = _agent_recommended(agent_findings, "acoustic_intelligence")
    if "QUIETER" in acoustic_action or "NOISE" in acoustic_action:
        return "IMPROVE_AUDIO_ENVIRONMENT"

    language_status = _agent_status(agent_findings, "regional_language")
    if language_status == "WARNING":
        return "CONTINUE_IN_PREFERRED_LANGUAGE"

    mapping = {
        "REQUEST_LONGER_RECORDING": "COLLECT_MORE_SPEECH",
        "REQUEST_QUIETER_ENVIRONMENT": "IMPROVE_AUDIO_ENVIRONMENT",
        "SPEAK_CLOSER_TO_MIC": "RETRY_RECORDING",
        "REDUCE_MICROPHONE_GAIN": "RETRY_RECORDING",
        "REQUEST_FRESH_RECORDING": "RETRY_RECORDING",
        "RETRY_VERIFICATION_SERVICE": "RETRY_UPLOAD",
    }
    if legacy in mapping:
        return mapping[legacy]

    if "SESSION_EXPIRED" in reasons:
        return "RETRY_RECORDING"
    return "RETRY_RECORDING"


def allowed_actions_for(outcome: str, baseline_action: Optional[str]) -> List[str]:
    """Gemini may only choose within this security-preserving set."""
    if outcome == "VERIFIED":
        return []
    if outcome == "BLOCKED":
        return ["HUMAN_REVIEW"]
    if baseline_action == "HUMAN_REVIEW":
        return ["HUMAN_REVIEW"]
    if baseline_action == "INDEPENDENT_VERIFICATION":
        return ["INDEPENDENT_VERIFICATION", "HUMAN_REVIEW"]
    if baseline_action == "RETRY_UPLOAD":
        return ["RETRY_UPLOAD", "RETRY_RECORDING", "INDEPENDENT_VERIFICATION"]
    if baseline_action == "CONTINUE_IN_PREFERRED_LANGUAGE":
        return ["CONTINUE_IN_PREFERRED_LANGUAGE", "RETRY_RECORDING", "INDEPENDENT_VERIFICATION"]
    return [
        "COLLECT_MORE_SPEECH",
        "RETRY_RECORDING",
        "IMPROVE_AUDIO_ENVIRONMENT",
        "CONTINUE_IN_PREFERRED_LANGUAGE",
        "INDEPENDENT_VERIFICATION",
    ]


@dataclass
class RecoveryPlan:
    outcome: str
    action: Optional[str]
    customer_message: str
    preferred_language: str
    allowed_actions: List[str] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)
    source: str = "deterministic"
    validation_errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "outcome": self.outcome,
            "recovery_action": self.action,
            "customer_message": self.customer_message,
            "preferred_language": self.preferred_language,
            "allowed_actions": list(self.allowed_actions),
            "reasons": list(self.reasons),
            "source": self.source,
            "validation_errors": list(self.validation_errors),
        }


def _language_message_ok(message: str, language: str) -> bool:
    if not message:
        return False
    if language == "en":
        return bool(re.search(r"[A-Za-z]", message))
    low, high = _SCRIPT_RANGES.get(language, ("", ""))
    return any(low <= ch <= high for ch in message) if low else True


def validate_gemini_message(message: str, language: str, outcome: str) -> List[str]:
    errors: List[str] = []
    text = str(message or "").strip()
    if not (8 <= len(text) <= 400):
        errors.append("MESSAGE_LENGTH_INVALID")
    if _SECRET_REQUEST_RE.search(text):
        errors.append("SECRET_REQUEST_FORBIDDEN")
    if outcome != "VERIFIED" and _FALSE_VERIFICATION_RE.search(text):
        errors.append("FALSE_VERIFICATION_CLAIM")
    if not _language_message_ok(text, language):
        errors.append("LANGUAGE_MISMATCH")
    if "http://" in text.lower() or "https://" in text.lower():
        errors.append("EXTERNAL_LINK_FORBIDDEN")
    return errors


def build_plan(
    *,
    verification_status: Optional[str],
    decision: Optional[str],
    session_state: Optional[str],
    reason_codes: Optional[Iterable[str]] = None,
    legacy_recovery_action: Optional[str] = None,
    agent_findings: Optional[Dict[str, Any]] = None,
    preferred_language: Optional[str] = None,
) -> RecoveryPlan:
    lang = normalize_language(preferred_language)
    reasons = [str(r) for r in (reason_codes or [])]
    outcome = derive_outcome(verification_status, decision, session_state, reasons)
    action = derive_action(
        outcome=outcome,
        recovery_action=legacy_recovery_action,
        reason_codes=reasons,
        agent_findings=agent_findings,
    )
    message = template_message(action, lang) if action else ""
    if outcome == "VERIFIED":
        # Verified sessions should not be nudged into recovery; use a neutral confirmation.
        message = {
            "en": "Voice authentication successful.",
            "hi": "आवाज़ सत्यापन सफल रहा।",
            "ta": "குரல் சரிபார்ப்பு வெற்றிகரமாக முடிந்தது.",
            "kn": "ಧ್ವನಿ ಪರಿಶೀಲನೆ ಯಶಸ್ವಿಯಾಗಿದೆ.",
            "te": "స్వర ధృవీకరణ విజయవంతమైంది.",
            "gu": "અવાજ ચકાસણી સફળ થઈ.",
        }[lang]
    return RecoveryPlan(
        outcome=outcome,
        action=action,
        customer_message=message,
        preferred_language=lang,
        allowed_actions=allowed_actions_for(outcome, action),
        reasons=reasons,
    )


def apply_gemini_selection(
    plan: RecoveryPlan,
    gemini_data: Optional[Dict[str, Any]],
) -> RecoveryPlan:
    """
    Validate Gemini's proposed action/message against deterministic policy.
    Invalid proposals fall back to the deterministic plan (never fail open).
    """
    if not gemini_data or plan.outcome == "VERIFIED" or not plan.action:
        return plan

    proposed_action = str(gemini_data.get("action") or "").strip().upper()
    proposed_message = str(gemini_data.get("message") or "").strip()
    errors: List[str] = []
    action_ok = False

    if proposed_action not in APPROVED_ACTIONS:
        errors.append("ACTION_NOT_APPROVED")
    elif proposed_action not in plan.allowed_actions:
        errors.append("ACTION_DOWNGRADE_BLOCKED")
    else:
        plan.action = proposed_action
        action_ok = True

    message_errors = validate_gemini_message(proposed_message, plan.preferred_language, plan.outcome)
    if message_errors:
        errors.extend(message_errors)
    if message_errors or not action_ok:
        # Keep the deterministic localized template if the LLM proposal is unsafe.
        plan.customer_message = template_message(plan.action, plan.preferred_language)
    else:
        plan.customer_message = proposed_message

    plan.allowed_actions = allowed_actions_for(plan.outcome, plan.action)
    plan.validation_errors = errors
    plan.source = "gemini" if not errors else "gemini_action_with_template_fallback"
    return plan
