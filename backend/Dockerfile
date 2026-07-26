FROM python:3.13-slim

# libsndfile backs soundfile; ffmpeg lets librosa decode mp3/m4a uploads
RUN apt-get update \
    && apt-get install -y --no-install-recommends libsndfile1 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8001

# Analysis is offloaded to a thread pool, so one worker serves concurrent
# requests fine; scale with replicas rather than threads for CPU-bound work.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
