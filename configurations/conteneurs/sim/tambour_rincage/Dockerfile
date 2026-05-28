FROM python:3.11-slim
WORKDIR /app

# 1. On copie le fichier requirements.txt en premier
COPY requirements.txt .

# 2. On installe les dépendances 
RUN pip install --no-cache-dir -r requirements.txt

# 3. On copie le reste du code source
COPY . .

EXPOSE 502
CMD ["python", "-u", "app.py"]