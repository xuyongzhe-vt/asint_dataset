#!/bin/bash

source deepseek_env/bin/activate

free_port=$(python -c 'import socket; s=socket.socket(); s.bind(("",0)); print(s.getsockname()[1]); s.close()')
echo "Picked free port: $free_port"

screen -dmS tunnel bash -c "ssh -N -R 18001:localhost:${free_port} ${ENTRY_HOST}"

python -m vllm.entrypoints.openai.api_server \
  --model deepseek-ai/DeepSeek-R1-Distill-Qwen-32B \
  --max-model-len 10000 \
  --port ${free_port} \
  --tensor-parallel-size 2 \
  --host 0.0.0.0 &
llm_pid=$!

API_URL="http://localhost:${free_port}/v1/models"
CHECK_INTERVAL=30

echo "⌛ Waiting for LLM server to become ready at $API_URL"
while true; do
    if ! kill -0 $llm_pid 2>/dev/null; then
        echo "❌ vLLM server failed to start (PID $llm_pid not running)"
        exit 1
    fi

    if curl -s --max-time 5 "$API_URL" | grep -q '"object"'; then
        echo "✅ LLM server is up!"
        exit 0   # return control to caller
    else
        echo "⏳ Server not ready yet, retrying in $CHECK_INTERVAL seconds ..."
        sleep $CHECK_INTERVAL
    fi
done
