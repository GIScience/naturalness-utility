FROM python:3.11.4-bookworm

ENV PACKAGE_NAME='datafusion'

RUN pip install --no-cache-dir poetry==1.8.3

COPY pyproject.toml poetry.lock ./

RUN  poetry install --no-ansi --no-interaction --all-extras --without dev

COPY $PACKAGE_NAME $PACKAGE_NAME
COPY app app

SHELL ["/bin/bash", "-c"]
ENTRYPOINT poetry run python app/api.py

EXPOSE 8000
