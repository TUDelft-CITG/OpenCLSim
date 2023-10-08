# use python package as base
FROM python:3.9-slim
ARG GITHUB_TOKEN

# upgrade packages
RUN apt update && apt install -y git procps build-essential libgeos-dev libgeos-c1v5

# Upgrade pip
RUN pip install --upgrade pip

# Install notebook
RUN pip install jupyter notebook

RUN echo 'alias la="ls -la"' >> ~/.bashrc
RUN echo 'alias jn="jupyter notebook --ip 0.0.0.0 --allow-root --no-browser --port=8888"' >> ~/.bashrc

# install python package
WORKDIR /openclsim
ADD . /openclsim
RUN pip install -e .

CMD ["sh", "-c", "tail -f /dev/null"]
