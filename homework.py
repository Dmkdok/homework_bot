import logging
import os
import sys
import time

from dotenv import load_dotenv
import requests
from telebot import TeleBot

from exceptions import APIResponseError, WorkStatusError, WorkKeyError

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка доступности переменных окружения."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }

    missing_tokens = [
        token_name
        for token_name, token_value in tokens.items()
        if not token_value
    ]

    return missing_tokens


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
        logger.debug(f'Бот отправил сообщение: {message}')

    except Exception as error:
        logger.error(f'Сбой при отправке сообщения в Telegram: {error}')


def get_api_answer(timestamp):
    """Делает запрос к API-сервиса."""
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
        if response.status_code != 200:
            error_message = (
                f'Сбой в работе программы.\n'
                f'Эндпоинт {ENDPOINT} недоступен.\n'
                f'Код ответа: {response.status_code}'
            )
            logger.error(error_message)
            raise APIResponseError(error_message)

        return response.json()

    except requests.RequestException as error:
        error_message = f'Ошибка при запросе к API: {error}'
        logger.error(error_message)
        raise APIResponseError(error_message)


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError('Ответ API не является словарем')

    if 'homeworks' not in response or 'current_date' not in response:
        error_message = 'Отсутствуют ожидаемые ключи в ответе API'
        logger.error(error_message)
        raise WorkKeyError(error_message)

    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError('Поле "homeworks" не является списком')
    return homeworks


def parse_status(homework):
    """Извлечение статуса домашней работы."""
    try:
        homework_name = homework['homework_name']
        homework_status = homework['status']
    except KeyError as key:
        error_message = f'В ответе API отсутствует ключ: {key}'
        logger.error(error_message)
        raise WorkKeyError(error_message)

    if homework_status not in HOMEWORK_VERDICTS:
        error_message = f'Неизвестный статус работы: {homework_status}'
        logger.error(error_message)
        raise WorkStatusError(error_message)

    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    missing_tokens = check_tokens()
    if missing_tokens:
        logging.critical(
            'Отсутствуют обязательные переменные окружения: '
            f'{", ".join(missing_tokens)}\n'
            'Программа принудительно остановлена.')
        sys.exit(1)

    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_error = None

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)

            if homeworks:
                message = parse_status(homeworks[0])
                send_message(bot, message)
            else:
                logger.debug('Нет новых статусов')

            timestamp = response.get('current_date', timestamp)

        except Exception as error:

            if str(error) != str(last_error):
                send_message(bot, error)
                last_error = error

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
