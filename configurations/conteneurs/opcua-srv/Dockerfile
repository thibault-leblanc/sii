FROM python:3.11-slim
WORKDIR /app

# Installation des dépendances système nécessaires pour compiler "cryptography"
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Installation des dépendances Python
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir asyncua==1.1.5

# Copie des scripts
COPY . .

# Lancement sans mise en cache de l'affichage (logs instantanés)
CMD ["python", "-u", "app.py"]