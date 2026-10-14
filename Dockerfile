FROM python:3.13-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src

# Instagram session (cookies.txt, user_agent.txt) lives here; mount it as a volume.
# Create it with: docker run -it --rm -v $PWD/data:/app/data --env-file .env <image> python src/ig_login.py
VOLUME /app/data

CMD ["python", "src/main.py"]
