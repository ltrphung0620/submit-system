import pytest
from pydantic import ValidationError

from app.config import Settings


def test_api_key_mode_requires_two_distinct_keys() -> None:
    with pytest.raises(ValidationError, match="SALAMANDERS_KEY and UI_SHARED_KEY are required"):
        Settings(auth_mode="api_key", salamanders_key="", ui_shared_key="")

    with pytest.raises(ValidationError, match="must be different"):
        Settings(
            auth_mode="api_key",
            salamanders_key="same-secret",
            ui_shared_key="same-secret",
        )

    settings = Settings(
        auth_mode="api_key",
        salamanders_key="salamanders-secret",
        ui_shared_key="ui-shared-secret",
    )
    assert settings.salamanders_key.get_secret_value() == "salamanders-secret"
    assert settings.ui_shared_key.get_secret_value() == "ui-shared-secret"
