FROM pulumi/pulumi-python:latest

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt ./

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy your Pulumi project files into the container
COPY Pulumi.yaml .
COPY Pulumi.*.yaml ./
COPY __main__.py .
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["preview"]