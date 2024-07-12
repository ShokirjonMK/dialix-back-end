FROM tiangolo/uvicorn-gunicorn:python3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y ffmpeg libpq-dev \
#    && apt-get update && apt-get install -y audiowaveform \
#    && add-apt-repository ppa:deadsnakes/ppa \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --upgrade pip

COPY requirements.txt /app/
RUN pip install -r requirements.txt

RUN useradd -m myuser
USER myuser

COPY . . 
#COPY backend /app/backend
#COPY migrations /app/migrations
#COPY uploads /app/uploads
#COPY workers /app/workers
