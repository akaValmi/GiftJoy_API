# Usa una imagen base adecuada para tu aplicación
FROM python:3.12-slim

# Instala las dependencias necesarias, añade la clave GPG, y elimina paquetes conflictivos
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    apt-transport-https \
    ca-certificates \
    gnupg2 && \
    curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/debian/11/prod.list | tee /etc/apt/sources.list.d/msprod.list && \
    apt-get update && \
    apt-get install -y \
    unixodbc \
    unixodbc-dev \
    gcc && \
    ACCEPT_EULA=Y apt-get install -y msodbcsql18 && \
    apt-get -f install && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Configura el entorno de trabajo
WORKDIR /app

# Copia los archivos de tu aplicación al contenedor
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Expone el puerto que tu aplicación usará
EXPOSE 8000

# Comando para ejecutar tu aplicación
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
