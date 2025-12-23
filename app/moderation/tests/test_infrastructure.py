import pytest

from app.moderation.infrastructure.local import LocalDictionaryModerator


@pytest.mark.unit
class TestLocalDictionaryModerator:
    @pytest.mark.parametrize(
        "content,expected_verdict,profanity_list,should_find_word",
        [
            ("Mensagem limpa e educada", "APPROVED", ["idiota", "bobo"], None),
            ("Você é um idiota", "REJECTED", ["idiota", "bobo"], "idiota"),
            ("Você é um IDIOTA", "REJECTED", ["idiota"], "idiota"),
            ("BOBO e IDIOTA juntos", "REJECTED", ["bobo", "idiota"], "bobo"),
        ],
        ids=["clean_content", "contains_profanity", "case_insensitive", "multiple_profanity"],
    )
    def test_moderate_content(self, settings, content, expected_verdict, profanity_list, should_find_word):
        settings.PROFANITY_LIST = profanity_list
        moderator = LocalDictionaryModerator()

        result = moderator.moderate(content)

        assert result["verdict"] == expected_verdict
        assert result["provider"] == "local_dictionary"
        assert result["score"] == 1.0

        if should_find_word:
            assert should_find_word in result["details"]["reason"]
