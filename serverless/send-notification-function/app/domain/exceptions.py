"""Excepciones del dominio de notificaciones."""


class DomainError(Exception):
    """Base de los errores del dominio."""


class InvalidNotificationError(DomainError):
    """Un NotificationRecord viola una regla del dominio."""
