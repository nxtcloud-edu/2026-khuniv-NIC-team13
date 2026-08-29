from pathlib import Path

from app.config.settings import Settings


def test_env_example_covers_every_runtime_setting_alias():
    env_example = Path(__file__).parents[1] / ".env.example"
    configured_keys = {
        line.split("=", 1)[0].strip()
        for line in env_example.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#") and "=" in line
    }
    setting_aliases = {
        field.validation_alias
        for field in Settings.model_fields.values()
        if isinstance(field.validation_alias, str)
    }

    assert setting_aliases <= configured_keys
    assert {"LOG_LEVEL", "VERBOSE_LIBS"} <= configured_keys
    assert {
        "OPENAI_API_KEY",
        "OPENAI_CHAT_MODEL",
        "OPENAI_REASONING_EFFORT",
    } <= configured_keys
    assert {
        "EMBEDDING_PROVIDER",
        "FRIENDLI_API_KEY",
        "FRIENDLI_BASE_URL",
        "EXAONE_CHAT_MODEL",
        "UPSTAGE_API_KEY",
        "UPSTAGE_BASE_URL",
        "UPSTAGE_EMBEDDING_QUERY_MODEL",
        "UPSTAGE_EMBEDDING_PASSAGE_MODEL",
        "UPSTAGE_EMBEDDING_DIMENSION",
        "UPSTAGE_S3_VECTORS_INDEX",
    }.isdisjoint(configured_keys)
