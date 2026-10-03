FROM python:3.14-slim

RUN apt-get update && apt-get install -y \
    libgl1 \
    libegl1 \
    libgles2 \
    libglib2.0-0 \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 폰트 파일이 실제로 Docker 안에 들어왔는지 확인
RUN echo "===== /app 전체 =====" && find /app -maxdepth 3 -type f -print

CMD ["python", "main.py"]
