from logs.models import Log


def get_client_ip(request):
    """Extrai o IP real do cliente mesmo atrás de proxy."""
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def get_device(request):
    """Retorna o User-Agent resumido para rastreabilidade (RF28)."""
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    return user_agent[:200]


def register_log(request, action, model_name, object_id, details=None):
    """
    Cria um registro de log automático com IP e dispositivo (RF28 / RNF14).
    Uso: register_log(request, 'create', 'Occurrence', occ.id, {'title': occ.title})
    """
    Log.objects.create(
        user=request.user if request.user.is_authenticated else None,
        action=action,
        model_name=model_name,
        object_id=object_id,
        details=details or {},
        ip_address=get_client_ip(request),
        device=get_device(request),
    )
