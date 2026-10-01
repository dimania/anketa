#
# Build final image
#

FROM alpine:3.21

# set a directory for the app
WORKDIR /home/anketa

# copy all the files to the container
COPY . .
# install python dependencies
RUN apk add --no-cache python3 py3-pip
RUN python3 -m venv /home/anketa/venv
RUN . /home/anketa/venv/bin/activate
ENV PATH=/home/anketa/venv/bin:$PATH
RUN pip install --no-cache-dir -r requirements.txt
# Set timezone 
ENV TZ=Europe/Moscow
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

ARG ANKETA_UID=10001
ARG ANKETA_GID=10001
RUN addgroup -S -g ${ANKETA_GID} anketa \
    && adduser -S -u ${ANKETA_UID} -G anketa anketa \
    && chown -R anketa:anketa /home/anketa
USER anketa
