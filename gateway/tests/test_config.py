"""Validación de la configuración de Nginx (la imagen aplica la plantilla y después nginx la revisa)."""

from tests.gateway_containers import run_nginx_command


def test_nginx_configuration_is_valid(gateway_image: str) -> None:
    result = run_nginx_command(gateway_image, "-t")

    assert result.returncode == 0, result.stderr
    assert "syntax is ok" in result.stderr


def test_template_variables_are_replaced_with_defaults(gateway_image: str) -> None:
    # nginx -T muestra la configuración completa ya generada a partir de la plantilla.
    result = run_nginx_command(gateway_image, "-T")
    config = result.stdout

    assert result.returncode == 0, result.stderr
    assert "${" not in config  # ninguna variable quedó sin reemplazar
    assert "server host.docker.internal:8001 max_fails=0;" in config
    assert "server host.docker.internal:8002 max_fails=0;" in config
    assert "proxy_connect_timeout 2s;" in config
    assert "proxy_read_timeout    15s;" in config
    assert "rate=10r/s" in config
    assert "burst=20 nodelay" in config
