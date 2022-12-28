import logging
import sys
import time
from http import HTTPStatus

import requests
import telegram

from config import (ENDPOINT, HEADERS, HOMEWORK_VERDICTS, PRACTICUM_TOKEN,
                    RETRY_PERIOD, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN)
from exceptions import APIResponseError

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s, %(levelname)s, %(message)s'
)
handler.setFormatter(formatter)


def check_tokens():
    """Проверка доступности переменных окружения."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def send_message(bot, message):
    """Отправляет сообщения в Telegram."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.debug(f'Сообщение успешно отправлено {message}')
    except telegram.error.TelegramError as error:
        logger.error(f'Ошибка отправки сообщения {error}')


def get_api_answer(timestamp):
    """Получение ответа API."""
    timestamp = timestamp or int(time.time())
    params = {'from_date': timestamp}

    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except Exception as error:
        raise Exception(f'Эндпоинт не доступен: {error}')
    else:
        if response.status_code != HTTPStatus.OK:
            raise APIResponseError(
                f'Ошибка доступа к эндпоинту, статус {response.status_code}'
            )

    try:
        result = response.json()
    except requests.exceptions.JSONDecodeError:
        logger.error('Ошибка в формате json')
        raise requests.exceptions.JSONDecodeError('Ошибка в формате json')

    return result


def check_response(response):
    """Проверяет ответ API и возвращает список домашних работ."""
    if type(response) is not dict:
        raise TypeError('Ответ API не словарь')

    try:
        homeworks = response['homeworks']
    except KeyError as error:
        raise KeyError(f'В ответе API нет ключа {error}')

    if type(homeworks) is not list:
        raise TypeError(
            'В ответе API ключ homeworks - не список!'
        )

    return homeworks


def parse_status(homework):
    """Извлекает статус домашней работы.
    Возвращает строку для отправки в Telegram.
    """
    try:
        homework_name = homework['homework_name']
        homework_status = homework['status']
    except KeyError as error:
        raise KeyError(f'В ответе API нет ключа {error}')

    try:
        verdict = HOMEWORK_VERDICTS[homework_status]
    except KeyError as error:
        raise KeyError(f'Неизвестный статус работы {error}')

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
    empty_message = ''

    while True:
        try:
            response = get_api_answer(timestamp=timestamp)
            homeworks = check_response(response)
            if len(homeworks) == 0:
                logger.debug('Отсутствуют новые статусы в ответе API')
            else:
                for homework in homeworks:
                    send_message(bot=bot, message=parse_status(homework))

            timestamp = response.get(
                'current_date', int(time.time()) - RETRY_PERIOD
            )
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if empty_message != message:
                send_message(bot=bot, message=message)
                empty_message = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
