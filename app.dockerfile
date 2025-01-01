#########################################
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
    npm \
    sudo

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

USER pyuser
# Copy Python requirements and install
COPY --chown=pyuser:pyuser ./app/requirements.txt ./
RUN python -m pip install --user --no-cache-dir -r requirements.txt

# Copy package files and install dependencies
COPY --chown=pyuser:pyuser ./app/package*.json ./
RUN npm install

# Copy the rest of the application code
COPY --chown=pyuser:pyuser ./app/ ./

# Build static files
RUN npm run build
RUN python manage.py collectstatic --noinput

#########################################
# Test stage
FROM builder AS test

# Install system dependencies for Playwright
USER root
RUN apk add --no-cache \
    libstdc++ \
    chromium \
    chromium-chromedriver \
    nss \
    freetype \
    freetype-dev \
    harfbuzz \
    ttf-freefont \
    font-noto-emoji \
    ffmpeg 

# Create symlink for ffmpeg in the expected location
RUN mkdir -p /usr/lib/chromium/ffmpeg-1010 && \
    ln -s /usr/bin/ffmpeg /usr/lib/chromium/ffmpeg-1010/ffmpeg-linux && \
    chmod -R 777 /usr/lib/chromium

# Switch to pyuser for remaining operations
USER pyuser

# Install Playwright browsers - needed for recording
RUN npx playwright install chromium

# Set environment variables for test stage
ENV CHROME_BIN=/usr/bin/chromium-browser \
    CHROME_PATH=/usr/lib/chromium/ \
    PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0 \
    PLAYWRIGHT_BROWSERS_PATH=/usr/lib/chromium \
    FLASK_ENV=development \
    FLASK_DEBUG=1 \
    PATH="/usr/local/bin:/usr/bin:/bin:/home/pyuser/.local/bin:/usr/local/lib/node_modules/npm/bin:${PATH}"

# Install Python debug tools 
RUN python -m pip install --user ipdb

#########################################
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
COPY --from=builder /home/pyuser/app/start /home/pyuser/app/start

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/home/pyuser/.local/lib/python3.11/site-packages:${PYTHONPATH}" \
    PATH="/home/pyuser/.local/bin:${PATH}"

USER pyuser
EXPOSE 3000/tcp

# Use the startup script
CMD ["/home/pyuser/app/start"]
