# ByLed django backend

# Разработка

### Зависимости

1. Python 3.8+
2. Docker, Docker-compose

### Установка

1. Создаем виртуальную среду `python -m venv venv` (это не нужно делать при использовании pycharm, он уже ее создает
   сам)
2. Установка зависимостей `pip install -r compose/local/requirements.txt`


В корне проета (где файл `.gitignore`) необходимо создать файл `.env` и добавить в него следующие переменные:

```shell
# Django web
DEBUG=True
ALLOWED_HOSTS=web,localhost
SECRET_KEY=<Секретный ключ Django>
SITE_BASE_URL=http://localhost:8080
APP_NAME=Конфигуратор ByLed
LOG_FILENAME=./logs/log.txt
# EMAIL
EMAIL_HOST=smtp.eu.mailgun.org
EMAIL_PORT=587
EMAIL_HOST_USER=postmaster@hellfish.ru
EMAIL_HOST_PASSWORD=<API ключ к mailgun>
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False

```

3. Сборка `docker-compose -f local.yml build`
4. Запуск `docker-compose -f local.yml up`

### При первом запуске

1. Подключиться к контейнеру `docker-compose -f local.yml run web bash`
2. Перейти в папку `/code/byled`
2. Необходимо создать superuser'а командой `python manage.py createsuperuser`

Пример данных суперюзера для разработки:

email: admin@hellfish.ru

password: admin



### Запуск

Запустить проект можно командой `docker-compose -f local.yml up`