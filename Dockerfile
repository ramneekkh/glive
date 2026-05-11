FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend.py .
COPY index.html .
COPY style.css .
COPY app.js .
COPY faq.js .

# Cloud Run exposes port 8080 by default
ENV PORT 8080
EXPOSE 8080

CMD ["python3", "-u", "backend.py"]
