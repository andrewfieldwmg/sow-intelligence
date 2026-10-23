# Hugging Face Docker Space: Postgres 16 + pgvector, local embeddings, Gradio front end.
FROM pgvector/pgvector:pg16
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv \
    && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PGDATA=/home/user/pgdata PATH=/home/user/venv/bin:/usr/lib/postgresql/16/bin:$PATH
WORKDIR /home/user/app
RUN python3 -m venv /home/user/venv
COPY --chown=user requirements.txt requirements-app.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-app.txt
COPY --chown=user . .
# Download the embedding model and tokenizer at build time, not on first request.
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5')" \
 && python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')"
EXPOSE 7860
ENTRYPOINT []
CMD ["bash", "./start.sh"]
