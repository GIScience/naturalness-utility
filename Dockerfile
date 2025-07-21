FROM python:3.11.5-bookworm

ENV PACKAGE_NAME='naturalness'

RUN pip install --no-cache-dir poetry==1.8.4

COPY pyproject.toml poetry.lock ./

RUN  poetry install --no-ansi --no-interaction --all-extras --without dev,test --no-root

COPY README.md README.md
COPY conf conf
COPY app app
COPY $PACKAGE_NAME $PACKAGE_NAME

RUN poetry install --no-ansi --no-interaction --only-root

SHELL ["/bin/bash", "-c"]
ENTRYPOINT exec poetry run python app/api.py

EXPOSE 8000
