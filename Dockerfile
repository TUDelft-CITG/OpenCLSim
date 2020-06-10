# Start with docker image from anaconda
FROM conda/miniconda3

# Install conda stuff first
RUN conda install numpy pandas nomkl pyproj enum34
# Then install rest via pip
RUN pip install pint Flask dill

ADD . /OpenCLSim
WORKDIR /OpenCLSim

# Install the application
RUN pip install -e .

# expose port 5000
EXPOSE 5000
# Serve on port 5000
CMD openclsim serve --port 5000
