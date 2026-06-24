# Multi-stage build for Apollo Captive Payment Gateway
FROM python:3.11-slim as builder

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY app/ ./app/

# Make sure scripts are executable
ENV PATH=/root/.local/bin:$PATH

# Environment variables
ENV PAYMENT_URL=https://www.coronatel.com/
ENV HOST=0.0.0.0
ENV PORT=8000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:' + __import__('os').getenv('PORT', '8000') + '/health')"

# Run the application
CMD sh -c "python -m uvicorn app.main:app --host ${HOST} --port ${PORT} --log-level debug"
