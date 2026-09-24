# Backend image: bakes the policy corpus + ChromaDB collection in at build
# time (same approach as the Render deploy, see DEPLOYMENT.md) so the
# container starts ready to serve -- no ingestion step needed at runtime.
# This build step needs network access (downloads the RBC specimen PDFs and
# the local embedding model) but no API keys.
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python scripts/download_real_policies.py && python ingest.py

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
