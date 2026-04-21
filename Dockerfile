FROM python:3.11-slim
WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
COPY data/ ./data/
COPY tests/ ./tests/
COPY conftest.py ./

ENV DATA_DIR=/srv/data
ENV PYTHONPATH=/srv

RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /srv
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]