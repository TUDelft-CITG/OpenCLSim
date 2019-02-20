# Start with pyramid app image
FROM continuumio/miniconda3

# Install conda stuff first
RUN conda install numpy pandas nomkl pyproj
RUN pip install pint Flask

WORKDIR /Hydraulic-Infrastructure-Realisation
ADD . /Hydraulic-Infrastructure-Realisation

# Then install rest via pip
RUN python setup.py develop
CMD digital_twin serve --production
