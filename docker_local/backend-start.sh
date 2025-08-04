#!/bin/bash

WORKERS=${WORKERS:-1}
LANGFLOW_PORT=${LANGFLOW_PORT:-7860}
ENV=${ENV:-.env}

uv run uvicorn \
    --factory langflow.main:create_app \
    --host 0.0.0.0 \
    --port ${LANGFLOW_PORT} \
    --loop asyncio \
    --workers ${WORKERS}
    # --reload \
    # --env-file ${ENV} \