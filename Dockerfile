# use python package as base
FROM python:3.9-slim
ARG GITHUB_TOKEN

# upgrade packages
RUN apt update && apt install -y git procps
RUN pip install --upgrade pip

# install python package
WORKDIR /openclsim
ADD . /openclsim
RUN pip install -e .

EXPOSE 8888

CMD ["sh", "-c", "tail -f /dev/null"]
