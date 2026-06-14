FROM rocker/r-ver:4.4.2

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libcurl4-openssl-dev \
    libssl-dev \
    libxml2-dev \
    libgit2-dev \
    libsodium-dev \
    libuv1-dev \
    cmake \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

RUN Rscript -e "install.packages(c('plumber','jsonlite','dplyr','ggplot2','rpart'), repos='https://cloud.r-project.org')"

RUN Rscript -e "options(warn=2); install.packages('mlr3', repos='https://cloud.r-project.org', dependencies=TRUE)"
RUN Rscript -e "install.packages('mlr3learners', repos='https://cloud.r-project.org')"

RUN Rscript -e "library(mlr3); print('mlr3 OK')"
RUN Rscript -e "library(mlr3learners); print('mlr3learners OK')"

RUN Rscript -e "install.packages('ranger', repos='https://cloud.r-project.org')"
RUN Rscript -e "library(ranger); print('ranger OK')"

RUN Rscript -e "install.packages('quanteda', repos='https://cloud.r-project.org')"
RUN Rscript -e "install.packages('Matrix', repos='https://cloud.r-project.org')"
RUN Rscript -e "library(quanteda); library(Matrix); print('text packages OK')"
RUN Rscript -e "install.packages('httr', repos='https://cloud.r-project.org')"

COPY app/ ./

EXPOSE 8000

CMD ["Rscript", "-e", "pr <- plumber::plumb('plumber.R'); pr$run(host='0.0.0.0', port=8000)"]