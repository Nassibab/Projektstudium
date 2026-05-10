# Base Image mit R
FROM rocker/r-ver:4.3.1
# Arbeitsverzeichnis
WORKDIR /app

# System dependencies (install the linux libraries needed for plumber)
RUN apt-get update && apt-get install -y \
    libcurl4-openssl-dev \
    libssl-dev \
    libxml2-dev \
    && rm -rf /var/lib/apt/lists/*

# Installiere plumber
RUN R -e "install.packages('plumber')"

# Installiere jsonlite
RUN R -e "install.packages('jsonlite')"

# Kopiere API Datei
COPY app/ app/

# Port freigeben
EXPOSE 8000

# Startkommando
CMD ["R", "-e", "pr <- plumber::plumb('app/plumber.R'); pr$run(host='0.0.0.0', port=8000)"]