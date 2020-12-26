FROM tiangolo/uvicorn-gunicorn-fastapi:python3.7-alpine3.8
COPY ./app /app
RUN apk add ffmpeg git musl-dev gcc
RUN pip install -r /app/requirements.txt

