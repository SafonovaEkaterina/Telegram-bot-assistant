# Telegram-bot ассистент

Telegram-bot для отслеживания статуса домашней работы на Яндекс.Практикум.
Увежомляет, когда статус изменен - взят на проверку, есть замечания, зачтено.

## Технологии:
- Python 3.8
- Python-dotenv 0.19.0
- Python-telegram-bot 13.7

## Как запустить проект:
Клонировать репозиторий:
```
git clone https://github.com/SafonovaEkaterina/Telegram-bot-assistant.git
```
Cоздать и активировать виртуальное окружение:
```
python -m venv venv
. venv/Scripts/activate
```
Установить зависимости из файла requirements.txt:
```
python -m pip install --upgrade pip
pip install -r requirements.txt
```
Записать в переменные окружения (файл .env) необходимые ключи:
- Токен профиля на Яндекс.Практикуме
- Токен телеграм-бота
- Свой ID-чата в телеграме

Запустить проект:
```
python homework.py
```
