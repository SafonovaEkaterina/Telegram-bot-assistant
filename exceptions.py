class APIResponseError(Exception):
    """Исключение ошибки доступа к эндроинту."""
    pass


class MassageNotSentError(Exception):
    """Кастомная ошибка сообщения."""

    pass


class RequestAPIError(Exception):
    """Ошибка при запросе к основному API."""
    pass


class CurrentDateError(Exception):
    """Ошибка при отсутствии current_date в ответе API."""
    pass
