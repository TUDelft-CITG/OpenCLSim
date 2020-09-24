# Start with docker image from anaconda
FROM continuumio/miniconda3:4.6.14

ADD . /openclsim
WORKDIR /openclsim

RUN conda install numpy pandas nomkl pyproj

RUN pip install --upgrade pip && \
    pip install -e .

EXPOSE 8888

CMD ["chmod", "700", "/openclsim/jupyter_notebook.sh"]
RUN echo 'alias jn="bash ./jupyter_notebook.sh"' >> ~/.bashrc