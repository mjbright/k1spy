#FROM python:3
FROM python:3.8.13-slim

WORKDIR /app

#apt-get install -y python3-pip bash vim && \
RUN apt-get update && \
    apt-get install -y bash vim && \
    /usr/bin/env python3 -m pip install kubernetes

RUN chsh -s /bin/bash && \
    mkdir -p /root

#USER user

ADD bashrc        /root/.bashrc
ADD k1s.py        .
ADD examples      .

CMD [ "/usr/bin/env", "python3", "./k1s.py" ]

