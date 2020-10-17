FROM centos:7

RUN yum upgrade -y && \
    yum install -y https://repo.ius.io/ius-release-el7.rpm epel-release && \
    yum install -y python36u python36u-devel python36u-pip nginx && \
    yum install -y python2-pip python-devel && \
    mkdir -p /app && \
    mkdir -p /certs

WORKDIR /app

RUN pip3.6 install -U pip setuptools && \
    pip install -U pip setuptools

COPY requirements.txt /app/requirements.txt
RUN pip3.6 install -r /app/requirements.txt && rm -f /app/requirements.txt

COPY requirements-py2.txt /app/requirements-py2.txt
RUN pip install -r /app/requirements-py2.txt && rm -f /app/requirements-py2.txt

COPY nginx.conf /etc/nginx/nginx.conf

COPY main.py /app/main.py

CMD [ "python3.6", "main.py" ]
