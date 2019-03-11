# Start with pyramid app image
FROM continuumio/miniconda3

# Install conda stuff first
RUN conda install numpy pandas nomkl pyproj
# Then install rest via pip
RUN pip install pint Flask dill

ADD . /Hydraulic-Infrastructure-Realisation
WORKDIR /Hydraulic-Infrastructure-Realisation

# Install the application
RUN pip install -e .

# expose port 80
EXPOSE 8080
# Serve on port 80
CMD digital_twin serve --port 8080
