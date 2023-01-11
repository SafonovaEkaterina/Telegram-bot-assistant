import logging
import sys
import time
from http import HTTPStatus

import requests
import telegram

from config import (ENDPOINT, ENVLIST, HEADERS, HOMEWORK_VERDICTS,
                    PRACTICUM_TOKEN, RETRY_PERIOD, TELEGRAM_CHAT_ID,
                    TELEGRAM_TOKEN)
from exceptions import (APIResponseError, CurrentDateError,
                        MassageNotSentError, RequestAPIError)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s, %(levelname)s, %(funcName)s, %(message)s'
)
handler.setFormatter(formatter)


def check_tokens():
    """Проверка доступности переменных окружения."""
    for i in ENVLIST:
        if not globals()[i]:
            logger.critical(
                f'Отсутствует обязательная переменная окружения: {i}'
            )
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отправляет сообщения в Telegram."""
    logging.info('Сообщение пользователю {TELEGRAM_CHAT_ID} отправляется')
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.debug(f'Сообщение успешно отправлено {message}')
    except telegram.error.TelegramError as error:
        logger.error(f'Ошибка отправки сообщения {error}')
        raise MassageNotSentError(f'Ошибка отправки сообщения {error}')


def get_api_answer(timestamp):
    """Получение ответа API."""
    logging.info('Запрос к API отправляется')
    timestamp = timestamp or int(time.time())
    params = {'from_date': timestamp}

    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except requests.exceptions.RequestException as error:
        raise RequestAPIError(f'Ошибка при запросе к основному API: {error}')
    else:
        if response.status_code != HTTPStatus.OK:
            raise APIResponseError(
                f'Эндпоинт недоступен, статус {response.status_code}'
            )

    try:
        result = response.json()
    except requests.exceptions.JSONDecodeError:
        raise requests.exceptions.JSONDecodeError('Ошибка в формате json')

    return result


def check_response(response):
    """Проверяет ответ API и возвращает список домашних работ."""
    logging.info('Начало проверки ответа сервера')
    if not isinstance(response, dict):
        raise TypeError('Ответ API не словарь')
    if response.get('current_date') is None:
        raise CurrentDateError('В ответе API отсутствует ключ current_date')

    try:
        homeworks = response['homeworks']
    except KeyError as error:
        raise KeyError(f'В ответе API нет ключа {error}')

    if not isinstance(homeworks, list):
        raise TypeError(
            'В ответе API ключ homeworks - не список!'
        )

    return homeworks


def parse_status(homework):
    """Извлекает статус домашней работы.

    Возвращает строку для отправки.
    """
    if 'homework_name' not in homework:
        raise KeyError(
            'Отсутствует ожидаемый ключ "homework_name" в ответе API.'
        )
    if 'status' not in homework:
        raise KeyError(
            'Отсутствует ожидаемый ключ "status" в ответе API.'
        )
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_VERDICTS:
        raise KeyError(f'Неизвестный статус работы {homework_status}')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        error = (
            'Обязательные переменные окружения отсутствуют. '
            'Принудительная остановка Бота'
        )
        logger.critical(error)
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_exception_message = ''

    while True:
        try:
            response = get_api_answer(timestamp=timestamp)
            homework = check_response(response)
            if len(homework) == 0:
                logger.debug('Отсутствуют новые статусы в ответе API')
            else:
                if last_exception_message != parse_status(homework[0]):
                    send_message(bot=bot, message=parse_status(homework[0]))

            timestamp = response.get('current_date')
        except MassageNotSentError as error:
            logger.error(error)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if last_exception_message != message:
                send_message(bot=bot, message=message)
                last_exception_message = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
