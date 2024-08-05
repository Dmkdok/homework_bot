class APIResponseError(Exception):
    """Исключение для ошибок в ответе API."""

    pass


class WorkKeyError(Exception):
    """Исключение для ошибок связанных с ключом работы."""

    pass


class WorkStatusError(Exception):
    """Исключение для ошибок при получении неизвестного статуса работы."""

    pass
