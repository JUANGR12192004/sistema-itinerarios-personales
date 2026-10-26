"""Configuración común de pytest."""

import pytest


@pytest.fixture
def anyio_backend() -> str:
    """Las pruebas marcadas con @pytest.mark.anyio se ejecutan con asyncio."""
    return "asyncio"
