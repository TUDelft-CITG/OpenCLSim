FROM continuumio/miniconda3

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y \
        build-essential \
        python3-dev \
        ffmpeg \
        git \
        libgdal-dev \
        gdal-bin && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Use a stable Python version for the teaching environment
RUN conda install -y python=3.12 gdal && \
    conda clean -afy

WORKDIR /workspaces/OpenCLSim

COPY . /workspaces/OpenCLSim

RUN python -m pip install --upgrade pip setuptools wheel

# Install the local OpenCLSim package first
RUN python -m pip install -e .

# Install the OpenTNSim version compatible with the current
# OpenCLSim development code
RUN python -m pip install "opentnsim==1.3.7"

# Notebook and teaching dependencies
RUN python -m pip install \
    "jupyter>=1.1.1" \
    "ipykernel>=6.29.5" \
    "ipywidgets>=8.1.7" \
    "jupyterlab_widgets>=3.0.15" \
    "notebook>=7.4.2" \
    "nbformat>=5.10.4" \
    "nbconvert>=7.16.6" \
    "matplotlib>=3.10.6" \
    "plotly>=6.3.0" \
    "pandas>=2.2.3" \
    "networkx>=3.5" \
    "simpy>=4.1.1" \
    "shapely>=2.1.2" \
    "pyproj>=3.7.2" \
    "deprecated>=1.2.18" \
    "folium>=0.20.0" \
    "ipyleaflet>=0.19.2" \
    "openpyxl>=3.1.5" \
    "contextily>=1.6.2" \
    "pyarrow>=21.0.0" \
    "momepy>=0.10.0"

CMD ["sleep", "infinity"]