.PHONY: build clean run logs solve debug

build:
	podman build -f Containerfile -t advent-of-claude-code:latest .

clean:
	podman stop advent-of-claude-code || true
	podman rm advent-of-claude-code || true
	podman rmi advent-of-claude-code:latest || true

run:
	@if [ -f .env ]; then \
		echo "Loading environment variables from .env"; \
		set -a; . $$(pwd)/.env; set +a; \
		podman run -d --name advent-of-claude-code \
			-e AOC_SESSION="$${AOC_SESSION:-}" \
			advent-of-claude-code:latest; \
	else \
		echo "Must provide env file with AOC_SESSION variable"; \
		exit 1; \
	fi

logs:
	podman logs -f advent-of-claude-code

solve:
	@if [ -z "$(YEAR)" ]; then \
		echo "Usage: make solve YEAR=2024 [DAY=1]"; \
		echo "  Provide YEAR to solve all 25 days"; \
		echo "  Provide YEAR and DAY to solve a specific day"; \
		exit 1; \
	fi
	@if [ -f .env ]; then \
		if [ -z "$(DAY)" ]; then \
			echo "Solving all days for AoC $(YEAR)..."; \
			set -a; . $$(pwd)/.env; set +a; \
			mkdir -p ./workspace; \
			podman run --rm -t \
				-e AOC_SESSION="$${AOC_SESSION:-}" \
				-e IS_SANDBOX=1 \
				-e PYTHONUNBUFFERED=1 \
				-v $$(pwd)/workspace:/app/agent_workspace:z \
				-v $$HOME/.claude:/root/.claude:z \
				advent-of-claude-code:latest \
				python -u src/main.py --year $(YEAR) --all-days; \
		else \
			echo "Solving AoC $(YEAR) Day $(DAY)..."; \
			set -a; . $$(pwd)/.env; set +a; \
			mkdir -p ./workspace; \
			podman run --rm -t \
				-e AOC_SESSION="$${AOC_SESSION:-}" \
				-e IS_SANDBOX=1 \
				-e PYTHONUNBUFFERED=1 \
				-v $$(pwd)/workspace:/app/agent_workspace:z \
				-v $$HOME/.claude:/root/.claude:z \
				advent-of-claude-code:latest \
				python -u src/main.py --year $(YEAR) --day $(DAY); \
		fi \
	else \
		echo "Must provide .env file with AOC_SESSION"; \
		exit 1; \
	fi

debug:
	@if [ -f .env ]; then \
		echo "Starting debug shell..."; \
		set -a; . $$(pwd)/.env; set +a; \
		mkdir -p ./workspace; \
		podman run --rm -it \
			-e AOC_SESSION="$${AOC_SESSION:-}" \
			-e IS_SANDBOX=1 \
			-e PYTHONUNBUFFERED=1 \
			-v $$(pwd)/workspace:/app/agent_workspace:z \
			-v $$HOME/.claude:/root/.claude:z \
			advent-of-claude-code:latest \
			/bin/bash; \
	else \
		echo "Must provide .env file with AOC_SESSION"; \
		exit 1; \
	fi
