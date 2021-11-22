# Start with docker image from anaconda
FROM continuumio/miniconda3:4.6.14

ADD . /OpenCLSim
WORKDIR /OpenCLSim

RUN conda install numpy pandas nomkl pyproj shapely setuptools

RUN pip install --upgrade pip && \
    pip install -e .[testing]

EXPOSE 8887

RUN echo 'alias jn="jupyter notebook --ip 0.0.0.0 --allow-root --no-browser --port=8887"' >> ~/.bashrc
CMD ["tail -f /dev/null"]
