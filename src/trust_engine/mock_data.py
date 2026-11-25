"""
Mock Data Generator for Member 2 API Simulation and Testing.
Updated to align with Phase 2 AudioQualityReport schemas.
"""

from src.schemas import (
    ActionRiskLevel,
    AudioQualityReport,
    AudioQualityStatus,
    AudioQualityIssue,
    RecommendedAction,
    MockVerificationEvidence,
)


class MockDataFactory:
    """Generates deterministic mock test cases for independent verification."""

    @staticmethod
    def get_clean_legitimate_caller() -> (MockVerificationEvidence, AudioQualityReport):
        evidence = MockVerificationEvidence(
            caller_id="user_89102",
            aletheia_liveness_score=0.96,
            aletheia_confidence=0.92,
            eidos_voice_match_score=0.94,
            eidos_confidence=0.95,
            requested_action_risk=ActionRiskLevel.HIGH,
            session_id="sess_mock_clean_001",
        )
        audio = AudioQualityReport(
            valid=True,
            quality_status=AudioQualityStatus.GOOD,
            suitable_for_authentication=True,
            duration_seconds=4.2,
            estimated_speech_duration_seconds=3.6,
            sample_rate=16000,
            channel_count=1,
            estimated_noise_level_dbfs=-55.0,
            estimated_snr_db=28.5,
            silence_percentage=14.3,
            clipping_percentage=0.0,
            rms_dbfs=-22.0,
            peak_amplitude=0.65,
            detected_issues=[],
            recommended_action=RecommendedAction.PROCEED,
            quality_notes=["Signal clean and adequate for voice biometrics"],
        )
        return evidence, audio

    @staticmethod
    def get_noisy_legitimate_caller() -> (MockVerificationEvidence, AudioQualityReport):
        evidence = MockVerificationEvidence(
            caller_id="user_89102",
            aletheia_liveness_score=0.88,
            aletheia_confidence=0.70,
            eidos_voice_match_score=0.82,
            eidos_confidence=0.68,
            requested_action_risk=ActionRiskLevel.MEDIUM,
            session_id="sess_mock_noisy_002",
        )
        audio = AudioQualityReport(
            valid=True,
            quality_status=AudioQualityStatus.MODERATE,
            suitable_for_authentication=True,
            duration_seconds=3.5,
            estimated_speech_duration_seconds=2.2,
            sample_rate=16000,
            channel_count=1,
            estimated_noise_level_dbfs=-34.0,
            estimated_snr_db=11.5,
            silence_percentage=37.1,
            clipping_percentage=0.0,
            rms_dbfs=-24.0,
            peak_amplitude=0.58,
            detected_issues=[AudioQualityIssue.EXCESSIVE_BACKGROUND_NOISE],
            recommended_action=RecommendedAction.REQUEST_QUIETER_ENVIRONMENT,
            quality_notes=["Elevated ambient noise; reduced biometrics confidence"],
        )
        return evidence, audio

    @staticmethod
    def get_deepfake_attack_caller() -> (MockVerificationEvidence, AudioQualityReport):
        evidence = MockVerificationEvidence(
            caller_id="user_victim_440",
            aletheia_liveness_score=0.12,
            aletheia_confidence=0.94,
            eidos_voice_match_score=0.91,
            eidos_confidence=0.90,
            requested_action_risk=ActionRiskLevel.HIGH,
            session_id="sess_mock_spoof_003",
        )
        audio = AudioQualityReport(
            valid=True,
            quality_status=AudioQualityStatus.GOOD,
            suitable_for_authentication=True,
            duration_seconds=3.5,
            estimated_speech_duration_seconds=3.1,
            sample_rate=16000,
            channel_count=1,
            estimated_noise_level_dbfs=-50.0,
            estimated_snr_db=24.0,
            silence_percentage=11.4,
            clipping_percentage=0.0,
            rms_dbfs=-20.0,
            peak_amplitude=0.72,
            detected_issues=[],
            recommended_action=RecommendedAction.PROCEED,
            quality_notes=["Signal clean; biometrics analysis valid"],
        )
        return evidence, audio

    @staticmethod
    def get_unusable_audio_caller() -> (MockVerificationEvidence, AudioQualityReport):
        evidence = MockVerificationEvidence(
            caller_id="user_unknown_000",
            aletheia_liveness_score=0.50,
            aletheia_confidence=0.20,
            eidos_voice_match_score=0.50,
            eidos_confidence=0.20,
            requested_action_risk=ActionRiskLevel.LOW,
            session_id="sess_mock_unusable_004",
        )
        audio = AudioQualityReport(
            valid=True,
            quality_status=AudioQualityStatus.POOR,
            suitable_for_authentication=False,
            duration_seconds=0.8,
            estimated_speech_duration_seconds=0.2,
            sample_rate=16000,
            channel_count=1,
            estimated_noise_level_dbfs=-18.0,
            estimated_snr_db=2.1,
            silence_percentage=75.0,
            clipping_percentage=12.5,
            rms_dbfs=-15.0,
            peak_amplitude=1.0,
            detected_issues=[
                AudioQualityIssue.INSUFFICIENT_DURATION,
                AudioQualityIssue.AUDIO_CLIPPING,
                AudioQualityIssue.INSUFFICIENT_SPEECH,
            ],
            recommended_action=RecommendedAction.REQUEST_FRESH_RECORDING,
            quality_notes=["Excessive clipping and extreme noise floor; insufficient speech"],
        )
        return evidence, audio
