# Start with pyramid app image
FROM continuumio/miniconda3

# Install conda stuff first
RUN conda install numpy pandas nomkl pyproj
# Then install rest via pip
RUN pip install pint Flask

ADD . /Hydraulic-Infrastructure-Realisation
WORKDIR /Hydraulic-Infrastructure-Realisation

# Install the application
RUN pip install -e .

# expose port 5000
EXPOSE 5000
# Serve on port 5000
CMD digital_twin serve --port 5000
