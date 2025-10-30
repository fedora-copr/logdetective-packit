FROM fedora:44

RUN dnf install -y \
  python3-pip \
  && dnf clean all

RUN mkdir /src

COPY . /src
WORKDIR /src

RUN pip install .

ENTRYPOINT gunicorn -c "./server/gunicorn.config.py" logdetective_packit.main:app

