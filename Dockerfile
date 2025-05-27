FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. copy application source
COPY app ./app
COPY dashboard/main.py ./dashboard/main.py

# 3. NEW: copy HTML templates & static assets
COPY dashboard/templates ./dashboard/templates
COPY dashboard/static     ./dashboard/static 

#COPY . .
CMD ["python", "app/service/server.py"]
