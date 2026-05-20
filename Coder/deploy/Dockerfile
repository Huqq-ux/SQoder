FROM python:3.11-slim

RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/

COPY . /opt/Coder/

WORKDIR /opt/Coder

RUN --mount=type=cache,target=/root/.cache/uv uv venv && \
    uv pip install --index-url https://mirror.sjtu.edu.cn/pytorch-wheels/cpu --link-mode=copy "torch>=2.0.0" && \
    uv pip install \
    --index-url https://mirrors.aliyun.com/pypi/simple/ \
    --link-mode=copy \
    langchain langchain-openai langchain-core langgraph pydantic \
    fastapi "uvicorn[standard]" python-multipart streamlit psutil mcp \
    sentence-transformers faiss-cpu huggingface-hub \
    langchain-community langchain-huggingface langchain-mcp-adapters \
    langgraph-checkpoint-postgres redis asyncpg "psycopg[binary,pool]" \
    httpx beautifulsoup4 lxml ddgs

ENV PYTHONPATH=/opt
ENV HF_ENDPOINT=https://hf-mirror.com
ENV HF_HOME=/opt/Coder/.cache/huggingface

RUN mkdir -p /opt/Coder/.cache/huggingface /opt/Coder/skills /opt/Coder/checkpoints /opt/Coder/knowledge/sop_docs

EXPOSE 8000
CMD ["/opt/Coder/.venv/bin/uvicorn", "Coder.server.main:app", "--host", "0.0.0.0", "--port", "8000"]
