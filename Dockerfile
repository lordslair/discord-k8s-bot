FROM alpine:3.19

RUN adduser -h /code -u 1000 -D -H discord

ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

COPY --chown=discord:discord requirements.txt /code/requirements.txt
COPY --chown=discord:discord /code            /code

WORKDIR /code
ENV PATH="/code/.local/bin:${PATH}"

RUN apk update --no-cache \
    && apk add --no-cache \
        "python3>=3.11" \
        "tzdata>=2023" \
    && apk add --no-cache --virtual .build-deps \
        "gcc=~12.2" \
        "libc-dev=~0.7" \
        "python3-dev>=3.11" \
    && su discord -c \
        "python3 -m ensurepip --upgrade && \
        pip3 install --user -U -r requirements.txt && \
        rm requirements.txt" \
    && apk del .build-deps

USER discord

ENTRYPOINT ["/code/main.py"]