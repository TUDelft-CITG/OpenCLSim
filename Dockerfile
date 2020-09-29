# Start with docker image from anaconda
FROM continuumio/miniconda3:4.6.14

ADD . /OPENCLSIM
WORKDIR /OPENCLSIM

RUN conda install numpy pandas nomkl pyproj

RUN pip install --upgrade pip && \
    pip install -r test-requirements.txt && \
    pip install -r additional-requirements.txt && \
    pip install -e .

EXPOSE 8887

CMD ["chmod", "700", "/OPENCLSIMssss/jupyter_notebook.sh"]
RUN echo 'alias jn="jupyter notebook --ip 0.0.0.0 --allow-root --no-browser --port=8887"' >> ~/.bashrc