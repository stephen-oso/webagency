#!/bin/bash
set -e

cd /app
celery -A app.workers.celery_app worker --loglevel=info --concurrency=4
