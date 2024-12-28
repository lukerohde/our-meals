# Build stage
FROM python:3.11-alpine AS builder

# Install system dependencies
RUN apk add --no-cache \
    python3-dev \
    postgresql-dev \
    postgresql-client \
    ca-certificates \
    curl \
    gcc \
    g++ \
    make \
    musl-dev \
    libffi-dev \
    npm

# Install latest npm
RUN npm install -g npm@latest

# Create and switch to a non-root user
RUN adduser -D pyuser && \
    mkdir -p /home/pyuser/.local/lib/python3.11/site-packages && \
    mkdir -p /home/pyuser/.local/bin && \
    mkdir -p /home/pyuser/app/node_modules && \
    chown -R pyuser:pyuser /home/pyuser

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/home/pyuser/.local/lib/python3.11/site-packages:${PYTHONPATH}" \
    PATH="/home/pyuser/.local/bin:${PATH}" \
    PIP_NO_CACHE_DIR=1 \
    PYTHON_VERSION=3.11

WORKDIR /home/pyuser/app

# Copy Python requirements and install
COPY --chown=pyuser:pyuser ./app/requirements.txt ./
USER pyuser
RUN python${PYTHON_VERSION} -m pip install --user --no-cache-dir -r requirements.txt

# Copy package files and install dependencies
COPY --chown=pyuser:pyuser ./app/package*.json ./
RUN npm install

# Copy the rest of the application code
COPY --chown=pyuser:pyuser ./app/ ./

# Build static files
RUN npm run build
RUN python manage.py collectstatic --noinput

# Test stage
FROM builder AS test
# This stage will be used for running tests
# Placeholder for future test setup with playwright and jest
RUN echo "Test stage - to be implemented with playwright and jest"
RUN python${PYTHON_VERSION} -m pip install --user ipdb

# Add sudo capability for npm global installs
USER root
RUN apk add --no-cache sudo && \
    echo "pyuser ALL=(ALL) NOPASSWD: /usr/local/bin/npm" >> /etc/sudoers

USER pyuser
# Make sure npm is available in PATH for test stage
ENV PATH="/usr/local/bin:/usr/bin:/bin:/home/pyuser/.local/bin:/usr/local/lib/node_modules/npm/bin:${PATH}"

# Production stage
FROM python:3.11-alpine AS production

# Install only the runtime dependencies
RUN apk add --no-cache libpq

RUN adduser -D pyuser
WORKDIR /home/pyuser/app

# Copy only what's needed from builder
COPY --from=builder /home/pyuser/.local /home/pyuser/.local
COPY --from=builder /home/pyuser/app/main /home/pyuser/app/main
COPY --from=builder /home/pyuser/app/ourmeals /home/pyuser/app/ourmeals
COPY --from=builder /home/pyuser/app/collectstatic /home/pyuser/app/collectstatic
COPY --from=builder /home/pyuser/app/templates /home/pyuser/app/templates
COPY --from=builder /home/pyuser/app/manage.py /home/pyuser/app/manage.py

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/home/pyuser/.local/lib/python3.11/site-packages:${PYTHONPATH}" \
    PATH="/home/pyuser/.local/bin:${PATH}"

USER pyuser
EXPOSE 3000/tcp

# Create startup script
COPY --chown=pyuser:pyuser <<EOF /home/pyuser/app/start.sh
#!/bin/sh
python manage.py migrate
python manage.py createsuperuser --noinput || true
exec gunicorn ourmeals.wsgi:application --bind 0.0.0.0:${PORT:-3000} --workers 3
EOF

RUN chmod +x /home/pyuser/app/start.sh

# Use the startup script
CMD ["/home/pyuser/app/start.sh"]
