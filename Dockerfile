FROM ubuntu
# Определяем переменные среды
# Чтобы python не создавал файлы .pyc
ENV PYTHONDONTWRITEBYTECODE=1
# Чтобы чтобы видеть выходные данные приложения в реальном времени
ENV PYTHONUNBUFFERED=1
ENV TZ="Europe/Moscow"
# Устанавливаем рабочую директорию
WORKDIR /code
RUN mkdir logs
COPY ./requirement.txt /code/
RUN chmod -R +x /code
# Установка cron
RUN apt update
RUN apt install -y python3 pip
# Обновляем pip устанавливаем зависимости
RUN pip config set global.trusted-host "pypi.org files.pythonhosted.org pypi.python.org"
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirement.txt

