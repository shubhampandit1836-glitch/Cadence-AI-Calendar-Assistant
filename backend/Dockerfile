FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=4000
ENV GIT_PYTHON_REFRESH=quiet
EXPOSE 4000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "4000"]