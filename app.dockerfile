# BASIC INSTALL
FROM python:3.13-slim
RUN apt-get update -qq
RUN apt-get install -qq python3-pip
RUN apt-get install -qq python3-dev libpq-dev 
RUN apt-get install -qq postgresql-client  

RUN adduser pyuser
USER pyuser
ENV PATH=/home/pyuser/.local/bin:"$PATH"

RUN mkdir /home/pyuser/app
WORKDIR /home/pyuser/app

COPY ./app/requirements.txt /home/pyuser/app/requirements.txt
RUN --mount=type=cache,target=/home/pyuser/.cache/pip,gid=1000,uid=1000 pip install --user -r ./requirements.txt

COPY ./app /home/pyuser/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
