FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv --no-cache-dir

COPY . /opt/Coder/

WORKDIR /opt/Coder

RUN uv venv && uv pip install \
    langchain langchain-openai langchain-core langgraph pydantic \
    fastapi "uvicorn[standard]" python-multipart streamlit psutil mcp \
    sentence-transformers faiss-cpu huggingface-hub \
    langchain-community langchain-huggingface langchain-mcp-adapters \
    langgraph-checkpoint-redis

ENV PYTHONPATH=/opt
ENV HF_ENDPOINT=https://hf-mirror.com
ENV HF_HOME=/opt/Coder/.cache/huggingface

RUN mkdir -p /opt/Coder/.cache/huggingface /opt/Coder/skills /opt/Coder/checkpoints /opt/Coder/knowledge/sop_docs

EXPOSE 8000
CMD ["/opt/Coder/.venv/bin/uvicorn", "Coder.server.main:app", "--host", "0.0.0.0", "--port", "8000"]
