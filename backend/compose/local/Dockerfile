FROM python:3.8
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8
ENV LANG=ru_RU.UTF-8
ENV XDG_RUNTIME_DIR=/export_tmp
ENV RUNLEVEL=3
RUN apt update
RUN apt install xfonts-base xfonts-75dpi -y
RUN wget  https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox_0.12.6-1.buster_amd64.deb
RUN dpkg -i wkhtmltox_0.12.6-1.buster_amd64.deb
RUN wkhtmltopdf -V



WORKDIR /code
RUN mkdir logs
RUN mkdir /export_tmp
COPY ./compose/local/requirements.txt /code
RUN pip install -r requirements.txt
COPY . /code
