"""Pruebas del adaptador de correo simulado."""

import logging

from app.infrastructure.notification.simulated_email_sender import SimulatedEmailSender


def test_el_envio_simulado_queda_en_el_log(caplog):
    with caplog.at_level(logging.INFO, logger="app"):
        SimulatedEmailSender().send("ana@example.com", "Hola Ana: tu itinerario quedó registrado.")

    assert "Correo simulado enviado a ana@example.com" in caplog.text
    assert "Hola Ana: tu itinerario quedó registrado." in caplog.text
