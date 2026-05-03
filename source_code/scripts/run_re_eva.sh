#!/bin/bash
SCRIPT_PATH="$(dirname "$0")/../llm_re_eva.py"

API_URL="http://localhost:8001/v1/models"
CHECK_INTERVAL=60   # seconds

echo "🔄 Waiting for LLM server at $API_URL ..."

while true; do
    if curl -s --max-time 5 "$API_URL" | grep -q '"object"'; then
        echo "✅ LLM server is up!"
        echo "🚀 Running main.py ..."

        if ! python3 "$SCRIPT_PATH"; then
            echo "Error: llm_classification.py failed" >&2
            exit 1
        fi

        if ! python3 "$SCRIPT_PATH"; then
            echo "Error: llm_classification.py failed" >&2
            exit 1
        fi

        if ! python3 "$SCRIPT_PATH"; then
            echo "Error: llm_classification.py failed" >&2
            exit 1
        fi

        if ! python3 "$SCRIPT_PATH"; then
            echo "Error: llm_classification.py failed" >&2
            exit 1
        fi

        if ! python3 "$SCRIPT_PATH"; then
            echo "Error: llm_classification.py failed" >&2
            exit 1
        fi

        if ! python3 "$SCRIPT_PATH"; then
            echo "Error: llm_classification.py failed" >&2
            exit 1
        fi
        exit 0
    else
        echo "⏳ Server not ready yet, retrying in $CHECK_INTERVAL seconds ..."
        sleep $CHECK_INTERVAL
    fi
done

echo "LLM re eva job finished"
