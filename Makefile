# Job-Market Intelligence Platform — task runner.
# Quickstart:  make demo   (offline, uses committed sample data)
.PHONY: help build up down clean ingest-sample scrape scrape-104 pipeline demo \
        urls psql mongosh logs ps

COMPOSE := docker compose
SPARK_SUBMIT := /opt/spark/bin/spark-submit --master local[*]

help:                ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

build:               ## Build all images (downloads Spark jars once)
	$(COMPOSE) build

up:                  ## Start the whole stack (MinIO, Mongo, Postgres, Spark, API, dashboard)
	$(COMPOSE) up -d --build
	@echo "Waiting for services to become healthy..."
	@sleep 5
	$(COMPOSE) ps

down:                ## Stop the stack (keep data volumes)
	$(COMPOSE) down

clean:               ## Stop the stack and delete all data volumes
	$(COMPOSE) down -v

ingest-sample:       ## Load committed sample_data into the lake (OFFLINE, no network)
	$(COMPOSE) run --rm api python -m scrapers.pipeline_to_lake --source govt
	$(COMPOSE) run --rm api python -m scrapers.pipeline_to_lake --source job104

scrape:              ## Scrape LIVE government open data into the lake (needs network)
	$(COMPOSE) run --rm api python -m scrapers.pipeline_to_lake --source govt --live

scrape-104:          ## Scrape LIVE 104.com.tw enrichment into the lake (needs network)
	$(COMPOSE) run --rm api python -m scrapers.pipeline_to_lake --source job104 --live

pipeline:            ## Run the PySpark batch pipeline (bronze -> silver -> gold marts)
	$(COMPOSE) exec -T spark $(SPARK_SUBMIT) spark_jobs/run_all.py

demo: up ingest-sample pipeline urls  ## One command: full offline end-to-end demo

urls:                ## Print the URLs to open
	@echo ""
	@echo "  Dashboard (Streamlit) : http://localhost:8501"
	@echo "  API docs  (FastAPI)   : http://localhost:8000/docs"
	@echo "  MinIO console         : http://localhost:9001  (minioadmin/minioadmin)"
	@echo ""

psql:                ## Open a psql shell on the gold marts
	$(COMPOSE) exec postgres psql -U jobmarket -d jobmarket

mongosh:             ## Open a mongo shell on the raw store
	$(COMPOSE) exec mongo mongosh jobmarket

logs:                ## Tail logs from all services
	$(COMPOSE) logs -f

ps:                  ## Show service status
	$(COMPOSE) ps
