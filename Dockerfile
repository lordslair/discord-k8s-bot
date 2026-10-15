FROM python:3.12-alpine

# Create user and group
RUN adduser -h /code -u 1000 -D -H discord

# Set environment variables
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/code/.local/bin:${PATH}"

# Copy only requirements to leverage Docker cache
COPY --chown=discord:discord /requirements.txt /code/requirements.txt

# Install dependencies (all available as musl wheels or pure Python: no compiler needed)
RUN su discord -c "pip install --user -r /code/requirements.txt"

# Copy application code
COPY --chown=discord:discord /code /code

# Set working directory
WORKDIR /code

# Set user
USER discord

# Entry point
ENTRYPOINT ["/code/main.py"]
