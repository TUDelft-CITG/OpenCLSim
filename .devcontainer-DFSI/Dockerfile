FROM continuumio/miniconda3:latest

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y \
        build-essential \
        git \
        curl \
        wget \
        libgeos-dev \
        libproj-dev \
        libgdal-dev \
        gdal-bin && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Use a known Python version for reproducibility
RUN conda install -y python=3.11 && \
    conda clean -afy

WORKDIR /workspaces/OpenCLSim

CMD ["sleep", "infinity"]