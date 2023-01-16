import logging
import sys
import time
from http import HTTPStatus

import requests
import telegram

from config import (ENDPOINT, ENVLIST, HEADERS, HOMEWORK_VERDICTS,
                    RETRY_PERIOD, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN)
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
    ok = True
    for env in ENVLIST:
        if not globals()[env]:
            logger.critical(
                f'Отсутствует обязательная переменная окружения: {env}'
            )
            ok = False
    return ok


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
    logging.info('Запрос к API c отправляется')
    timestamp = timestamp or 0
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
    if 'current_date' not in response:
        raise CurrentDateError('В ответе API отсутствует ключ current_date')
    if 'homeworks' not in response:
        raise KeyError('В ответе API нет ключа homeworks')

    homeworks = response['homeworks']

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
    timestamp = 0
    last_message = ''

    while True:
        try:
            response = get_api_answer(timestamp=timestamp)
            homeworks = check_response(response)
            if len(homeworks) == 0:
                logger.debug('Отсутствуют новые статусы в ответе API')
            else:
                message = parse_status(homeworks[0])
                if last_message != message:
                    send_message(bot=bot, message=message)
                    last_message = message

            timestamp = response.get('current_date')
        except MassageNotSentError as error:
            logger.error(error)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if last_message != message:
                send_message(bot=bot, message=message)
                last_message = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
