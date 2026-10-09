from functools import lru_cache

from bodyos_api.config import get_settings
from bodyos_api.crypto import FieldCipher
from bodyos_api.model_gateway import (
    CloudBaseAIHarness,
    CodexCLIHarness,
    HermesCLIHarness,
    RoutedModelGateway,
    UnavailableHarness,
    cloudbase_ai_settings_valid,
)


@lru_cache
def get_field_cipher() -> FieldCipher:
    encoded_key = get_settings().encryption_key.get_secret_value()
    if not encoded_key:
        raise RuntimeError("BODYOS_ENCRYPTION_KEY is required")
    return FieldCipher.from_base64(encoded_key)


@lru_cache
def get_model_gateway() -> RoutedModelGateway:
    settings = get_settings()
    cloudbase_key = settings.cloudbase_ai_api_key.get_secret_value()
    if (
        settings.private_wechat_cloud_enabled
        or settings.cloudbase_ai_env_id
        or cloudbase_key
        or settings.cloudbase_ai_model
    ):
        if not cloudbase_ai_settings_valid(
            settings.cloudbase_ai_env_id, cloudbase_key, settings.cloudbase_ai_model
        ):
            return RoutedModelGateway(UnavailableHarness(), UnavailableHarness())
        return RoutedModelGateway(
            CloudBaseAIHarness(
                env_id=settings.cloudbase_ai_env_id,
                api_key=cloudbase_key,
                model=settings.cloudbase_ai_model,
                timeout_seconds=settings.model_timeout_seconds,
            ),
            UnavailableHarness(),
        )
    return RoutedModelGateway(
        CodexCLIHarness(
            settings.codex_command,
            timeout_seconds=settings.model_timeout_seconds,
        ),
        HermesCLIHarness(
            settings.hermes_command,
            model=settings.hermes_model,
            timeout_seconds=settings.model_timeout_seconds,
        ),
    )
