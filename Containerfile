FROM fedora:44

# Default URL of Log Detective server assumes that
# container is running on the same node with default port
ENV LD_URL=0.0.0.0:8080

# All dependencies are installed primarily by pip
# the only exceptions should be those the deal with system settings
RUN dnf install -y \
  python3-pip \
  python3-fedora-messaging \
  fedora-messaging \
  && dnf clean all

RUN mkdir /src

# Copy Fedora messaging config to the default location
COPY ./server/conf.toml /etc/fedora-messaging/config.toml

#Copy source and other files to /src
COPY . /src

WORKDIR /src

RUN pip install .

ENTRYPOINT gunicorn -c "./server/gunicorn.config.py" logdetective_packit.main:app
