FROM python:3.11-slim

WORKDIR /app

# Install Node.js and npm (required for Claude Code)
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Claude Code CLI globally
RUN npm install -g @anthropic-ai/claude-code

# Create Claude config directory (credentials will be mounted at runtime)
RUN mkdir -p /root/.claude

COPY src/ ./src/

# Create agent workspace directory
RUN mkdir -p /app/agent_workspace

ENV PYTHONPATH=/app

CMD ["python", "src/main.py"]
