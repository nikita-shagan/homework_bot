import logging
import os
import time

import requests
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет наличие переменных окружения."""
    return bool(PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID)


def send_message(bot, message):
    """Отправляет сообщение в телеграм."""
    bot.send_message(TELEGRAM_CHAT_ID, message)
    logging.debug('Сообщение успешно отправлено.')


def get_api_answer(timestamp):
    """Делает запрос на получение статусов домашних работ."""
    try:
        res = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
    except requests.RequestException():
        raise Exception('Ошибка при выполнении запроса к серверу')

    if res.status_code != 200:
        raise Exception('Статус ответа сервера не равен 200')
    return res.json()


def check_response(response):
    """Проверяет документированность ответа."""
    if not isinstance(response, dict):
        raise TypeError('Тип ответа не словарь')
    homeworks = response.get('homeworks')
    if homeworks is None:
        raise Exception('Ответ не содержит поле homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('Тип значения поля homework не список')


def parse_status(homework):
    """Формирует сообщение для отправки в телеграм."""
    try:
        homework_name = homework['homework_name']
        verdict = HOMEWORK_VERDICTS[homework['status']]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except KeyError:
        raise Exception('Некорректный статус домашней работы')


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        message = 'Отсутствуют переменные окружения.'
        logging.critical(message)
        raise Exception(message)

    bot = Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            timestamp = response['current_date']
            for homework in response['homeworks']:
                send_message(bot, parse_status(homework))
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(bot, message)
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
