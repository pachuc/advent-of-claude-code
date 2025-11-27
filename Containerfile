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
COPY static/ ./static/

# Create agent workspace directory
RUN mkdir -p /app/agent_workspace

ENV PYTHONPATH=/app

# Expose port for web mode (only used with `make web`)
EXPOSE 8000

# Default command: CLI mode (web mode overrides with uvicorn)
CMD ["python", "-m", "src.main"]
