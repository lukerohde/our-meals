#!/bin/bash
set -e

# Print debug info
echo "Starting Pulumi deployment..."
echo "Stack: ${PULUMI_STACK:-dev}"

# Add Pulumi Python packages to PYTHONPATH
export PYTHONPATH=/pulumi/bin:$PYTHONPATH

# Configure state backend
if [ ! -z "$PULUMI_ACCESS_TOKEN" ]; then
    echo "Using Pulumi service backend..."
    pulumi login
elif [ ! -z "$PULUMI_BACKEND_URL" ]; then
    echo "Using custom backend: $PULUMI_BACKEND_URL"
    pulumi login "$PULUMI_BACKEND_URL"
else
    echo "Using local backend..."
    pulumi login --local
fi

# Select or create stack
STACK_NAME=${PULUMI_STACK:-dev}
echo "Selecting stack: $STACK_NAME"
pulumi stack select "$STACK_NAME" 2>/dev/null || pulumi stack init "$STACK_NAME"

# Run Pulumi command
echo "Running Pulumi command: $@"
exec pulumi $@
