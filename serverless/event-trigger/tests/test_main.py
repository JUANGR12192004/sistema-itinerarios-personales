"""Pruebas del proceso del trigger: reconexión, parada con Ctrl+C y ensamblaje."""

from pika.exceptions import AMQPConnectionError, StreamLostError

from app.application.delivery_handler import RetryPolicy
from app.config import Settings
from app.main import build_policy, run_with_reconnection
from tests.fakes import SleepRecorder


class ScriptedRun:
    """Simula consumer.run: cada llamada lanza la excepción dada o termina normalmente."""

    def __init__(self, *outcomes) -> None:
        self._outcomes = list(outcomes)
        self.calls = 0

    def __call__(self) -> None:
        self.calls += 1
        outcome = self._outcomes.pop(0)
        if outcome is not None:
            raise outcome


def test_se_reconecta_si_se_pierde_la_conexion_y_para_con_ctrl_c():
    run = ScriptedRun(AMQPConnectionError("refused"), StreamLostError("lost"), OSError("red"), KeyboardInterrupt())
    sleep = SleepRecorder()

    run_with_reconnection(run, reconnect_delay_seconds=5.0, sleep=sleep)

    assert run.calls == 4
    assert sleep.waits == [5.0, 5.0, 5.0]


def test_si_rabbitmq_cancela_el_consumo_tambien_se_reconecta():
    run = ScriptedRun(None, KeyboardInterrupt())
    sleep = SleepRecorder()

    run_with_reconnection(run, reconnect_delay_seconds=2.0, sleep=sleep)

    assert run.calls == 2
    assert sleep.waits == [2.0]


def test_ctrl_c_durante_la_espera_detiene_el_trigger():
    run = ScriptedRun(AMQPConnectionError("refused"))

    def interrupted_sleep(seconds: float) -> None:
        raise KeyboardInterrupt

    run_with_reconnection(run, reconnect_delay_seconds=5.0, sleep=interrupted_sleep)

    assert run.calls == 1


def test_la_politica_se_arma_con_la_configuracion():
    settings = Settings(
        trigger_infrastructure_attempts=4,
        trigger_function_error_attempts=2,
        trigger_retry_backoff_seconds=0.5,
        trigger_retry_max_backoff_seconds=3.0,
        trigger_requeue_delay_seconds=7.0,
    )

    assert build_policy(settings) == RetryPolicy(
        infrastructure_attempts=4,
        function_error_attempts=2,
        backoff_seconds=0.5,
        max_backoff_seconds=3.0,
        requeue_delay_seconds=7.0,
    )


def test_valores_por_defecto_de_la_configuracion(monkeypatch):
    for name in ("FUNCTION_INVOKE_URL", "TRIGGER_INFRASTRUCTURE_ATTEMPTS", "TRIGGER_REQUEUE_DELAY_SECONDS"):
        monkeypatch.delenv(name, raising=False)

    settings = Settings(_env_file=None)

    assert settings.function_invoke_url == "http://localhost:9000/2015-03-31/functions/function/invocations"
    assert settings.function_timeout_seconds == 15.0
    assert settings.trigger_infrastructure_attempts == 3
    assert settings.trigger_function_error_attempts == 3
    assert settings.trigger_requeue_delay_seconds == 10.0
