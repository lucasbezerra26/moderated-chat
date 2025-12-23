import pytest

from app.moderation.infrastructure.gemini import GeminiModerator
from app.moderation.infrastructure.local import LocalDictionaryModerator
from app.moderation.services.moderator import ModerationService


@pytest.mark.unit
class TestModerationService:

    def test_moderate_fallback_on_primary_failure(self, settings, monkeypatch):
        settings.MODERATION_PROVIDER = "gemini"
        settings.PROFANITY_LIST = []

        def mock_gemini_init(self):
            raise ValueError("API Key not configured")

        monkeypatch.setattr(GeminiModerator, "__init__", mock_gemini_init)

        result = ModerationService.moderate("teste")

        assert result["verdict"] == "APPROVED"
        assert result["provider"] == "local_dictionary"

    def test_moderate_system_fallback_on_all_failures(self, settings, monkeypatch):
        settings.MODERATION_PROVIDER = "gemini"

        def mock_gemini_init(self):
            raise ValueError("API Key not configured")

        def mock_local_init(self):
            raise Exception("Config error")

        monkeypatch.setattr(GeminiModerator, "__init__", mock_gemini_init)
        monkeypatch.setattr(LocalDictionaryModerator, "__init__", mock_local_init)

        result = ModerationService.moderate("teste")

        assert result["verdict"] == "REJECTED"
        assert result["provider"] == "system"
        assert "Todos os provedores falharam" in result["details"]["reason"]
