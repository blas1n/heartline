FROM python:3.11-slim AS builder

WORKDIR /app
COPY pyproject.toml .
RUN pip install poetry
RUN poetry export -o requirements.txt --without-hashes

FROM python:3.11-slim
WORKDIR /app

COPY --from=builder /app/requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE $PORT

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "$PORT"]