FROM python:3.11-slim

WORKDIR /

RUN apt-get update && apt-get install -y \
    libzbar0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8502

CMD ["streamlit", "run", "Main.py", "--server.port=8502", "--server.address=0.0.0.0"]