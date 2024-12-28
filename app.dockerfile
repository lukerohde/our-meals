# Build stage
FROM python:3.11-slim-bookworm as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3-dev \
    libpq-dev \
    postgresql-client \
    ca-certificates \
    curl \
    gnupg \
    gcc \
    g++ \
    make

# Install Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g npm@latest

# Create and switch to a non-root user
RUN adduser --disabled-password --gecos "" pyuser && \
    mkdir -p /home/pyuser/.local/lib/python3.11/site-packages && \
    mkdir -p /home/pyuser/.local/bin && \
    mkdir -p /home/pyuser/app/node_modules && \
    chown -R pyuser:pyuser /home/pyuser

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/home/pyuser/.local/lib/python3.11/site-packages:${PYTHONPATH}" \
    PATH="/home/pyuser/.local/bin:${PATH}" \
    PYTHON_VERSION=3.11

WORKDIR /home/pyuser/app

# Copy Python requirements and install
COPY --chown=pyuser:pyuser ./app/requirements.txt ./
USER pyuser
RUN python${PYTHON_VERSION} -m pip install --user -r requirements.txt

# Copy package files and install dependencies
COPY --chown=pyuser:pyuser ./app/package*.json ./
RUN npm install

# Copy the rest of the application code
COPY --chown=pyuser:pyuser ./app/ ./

# Build static files
RUN npm run build
RUN python manage.py collectstatic --noinput

# Test stage
FROM builder as test
# This stage will be used for running tests
# Placeholder for future test setup with playwright and jest
RUN echo "Test stage - to be implemented with playwright and jest"

# Production stage
FROM python:3.11-slim-bookworm as production

RUN adduser --disabled-password --gecos "" pyuser
WORKDIR /home/pyuser/app

# Copy only what's needed from builder
COPY --from=builder /home/pyuser/.local /home/pyuser/.local
COPY --from=builder /home/pyuser/app/main /home/pyuser/app/main
COPY --from=builder /home/pyuser/app/ourmeals /home/pyuser/app/ourmeals
COPY --from=builder /home/pyuser/app/staticfiles /home/pyuser/app/staticfiles
COPY --from=builder /home/pyuser/app/templates /home/pyuser/app/templates
COPY --from=builder /home/pyuser/app/manage.py /home/pyuser/app/manage.py

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/home/pyuser/.local/lib/python3.11/site-packages:${PYTHONPATH}" \
    PATH="/home/pyuser/.local/bin:${PATH}"

RUN apt-get update && apt-get install -y \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

USER pyuser
EXPOSE 3000/tcp

# Run with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:${PORT:-3000}", "our_meals.wsgi:application"]
