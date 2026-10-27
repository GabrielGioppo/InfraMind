from rest_framework.throttling import AnonRateThrottle


class PasswordResetThrottle(AnonRateThrottle):
    """Limita por IP os pedidos de recuperação de senha (taxa em settings: 'password_reset')."""
    scope = 'password_reset'
