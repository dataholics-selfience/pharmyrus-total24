FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY main.py .
COPY data_enrichment.py .
COPY google_patents_crawler.py .
COPY search_state.py .

# Railway uses PORT env variable
ENV PORT=8000

# Run with PORT from environment
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
