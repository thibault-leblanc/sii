FROM python:3.11-slim
WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir pymodbus==3.4.0
RUN pip install --no-cache-dir --no-compile cryptography
RUN pip install --no-cache-dir --no-compile asyncua==1.1.5

COPY . .
EXPOSE 502 4840
CMD ["python", "-u", "app.py"]