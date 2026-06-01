FROM rocker/r-ver:4.3.1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libcurl4-openssl-dev \
    libssl-dev \
    libxml2-dev \
    libgit2-dev \
    libsodium-dev \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

RUN Rscript -e "install.packages('plumber', repos='https://cloud.r-project.org')"
RUN Rscript -e "install.packages('jsonlite', repos='https://cloud.r-project.org')"
RUN Rscript -e "install.packages('dplyr', repos='https://cloud.r-project.org')"


COPY app/ app/

EXPOSE 8000

CMD ["Rscript", "-e", "pr <- plumber::plumb('app/plumber.R'); pr$run(host='0.0.0.0', port=8000)"]