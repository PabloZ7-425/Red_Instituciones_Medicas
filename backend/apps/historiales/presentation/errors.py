"""Framework-independent safe envelope; B5 will wire HTTP handlers to it."""
from apps.historiales.domain.errors import ErrorDominio


def error_response(error):
    if isinstance(error, ErrorDominio):
        return error.status, error.as_dict()
    return 500, ErrorDominio().as_dict()
