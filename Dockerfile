# "app" image: ingestion, loaders, FastAPI, Streamlit, and the analysis notebook.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# psycopg2-binary needs no build deps; keep the image slim.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Source is bind-mounted in docker-compose for live editing, but copy it so the
# image also works standalone.
COPY . .

EXPOSE 8000 8501
