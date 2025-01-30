FROM python:3.11-slim-bullseye
WORKDIR /app
COPY requirements.txt requirements.txt
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
COPY bot /app
ENTRYPOINT ["sh", "-c", "pybabel compile -d locales -D bot; wait-for-it -s $DB_ADDRESS:3306; alembic upgrade head; python main.py"]