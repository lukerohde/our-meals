# BASIC INSTALL
FROM python:3.11-slim-bookworm

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

# Set up the working directory
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

# Build static files for production
RUN if [ "$NODE_ENV" = "production" ] ; then \
        npm run build ; \
    fi
RUN python manage.py collectstatic --noinput

CMD ["python", "manage.py", "runserver", "0.0.0.0:3000"]
