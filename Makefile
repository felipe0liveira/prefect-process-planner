.PHONY: help setup clean example-simple example-parallel example-fanout example-create example-complex example-fallback example-cascade-skip

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Copy .env.example to .env and install dependencies
	cp -n .env.example .env || true
	uv sync

clean: ## Remove all saved outputs from data/
	rm -rf data/

# ---------------------------------------------------------------------------
# Examples
# ---------------------------------------------------------------------------

example-simple: ## Simple sequential: get user 1, then their posts
	uv run python -m src.main "Busque os dados do usuário 1 e depois liste os posts dele"

example-parallel: ## Parallel fan-out: get user 1, then posts AND todos in parallel
	uv run python -m src.main "Busque o usuário 1, depois liste os posts e os todos dele em paralelo"

example-fanout: ## Fan-out: get post 1, then fetch its comments; also get post 2 and its comments (both in parallel)
	uv run python -m src.main "Busque o post 1 e o post 2 em paralelo, depois busque os comentários de cada um"

example-create: ## Create a post for user 3
	uv run python -m src.main "Crie um post para o usuário 3 com título 'Hello World' e corpo 'Este é um teste'"

example-complex: ## Complex: list all users, pick user 5, get their posts, todos and comments on post 41
	uv run python -m src.main "Liste todos os usuários, depois busque o usuário 5, liste os posts do usuário 5, os todos do usuário 5, e os comentários do post 41, maximizando paralelismo"

example-fallback: ## Fallback: try to get user 999 (will fail), report error on failure
	uv run python -m src.main "Busque o usuário 999 e depois liste os posts dele. Se der erro em qualquer passo, reporte o erro"

example-cascade-skip: ## Cascade skip: fetch post 2 from unreliable service (fails), then get comments (skipped)
	uv run python -m src.main "Busque o post 2 usando o serviço instável, depois busque os comentários desse post, e também busque o usuário 1 em paralelo. Se der erro, reporte o erro"
