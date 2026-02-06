FROM alpine AS builder

# install python dependencies
RUN apk update
RUN apk add build-base
RUN apk add pkgconf


#
# Build final image
#

FROM alpine 

# set a directory for the app
WORKDIR /home/anketa

# copy all the files to the container
COPY . .
# install python dependencies
RUN apk update
RUN apk add python3
RUN apk add py3-pip
RUN python3 -m venv /home/anketa/venv
RUN . /home/anketa/venv/bin/activate
ENV PATH=/home/anketa/venv/bin:$PATH
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir pysocks
# Set timezone 
ENV TZ=Europe/Moscow
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
