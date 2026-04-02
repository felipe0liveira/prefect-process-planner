.PHONY: help setup clean preview plan execute run test readonly

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Copy .env.example to .env and install dependencies
	cp -n .env.example .env || true
	uv sync

clean: ## Remove all saved outputs from data/
	rm -rf data/

preview: ## Start local server to visualize DAGs at http://localhost:8080
	uv run uvicorn src.server:app --reload --port 8080

plan: ## Generate a DAG without executing — usage: make plan p="your prompt"
	@test -n "$(p)" || (echo "Error: missing prompt. Usage: make plan p=\"your prompt\"" && exit 1)
	uv run python -m src.main --plan "$(p)"

execute: ## Execute an existing DAG — usage: make execute d=20260401_143603
	@test -n "$(d)" || (echo "Error: missing run dir. Usage: make execute d=20260401_143603" && exit 1)
	uv run python -m src.main --execute "$(d)"

run: ## Generate and execute a DAG — usage: make run p="your prompt"
	@test -n "$(p)" || (echo "Error: missing prompt. Usage: make run p=\"your prompt\"" && exit 1)
	uv run python -m src.main "$(p)"

test: ## Test execution (blocks writes) — usage: make test p="your prompt"
	@test -n "$(p)" || (echo "Error: missing prompt. Usage: make test p=\"your prompt\"" && exit 1)
	uv run python -m src.main --test "$(p)"

readonly: ## Re-execute an existing DAG in readonly mode — usage: make readonly d=20260401_143603
	@test -n "$(d)" || (echo "Error: missing run dir. Usage: make readonly d=20260401_143603" && exit 1)
	uv run python -m src.main --execute "$(d)" --dry-run

# ---------------------------------------------------------------------------
# Examples
# ---------------------------------------------------------------------------

# uv run python -m src.main "Busque os dados do usuário 1 e depois liste os posts dele"
# uv run python -m src.main "Busque o usuário 1, depois liste os posts e os todos dele em paralelo"
# uv run python -m src.main "Busque o post 1 e o post 2 em paralelo, depois busque os comentários de cada um"
# uv run python -m src.main "Crie um post para o usuário 3 com título 'Hello World' e corpo 'Este é um teste'"
# uv run python -m src.main "Liste todos os usuários, depois busque o usuário 5, liste os posts do usuário 5, os todos do usuário 5, e os comentários do post 41, maximizando paralelismo"
# uv run python -m src.main "Busque o usuário 999 e depois liste os posts dele. Se der erro em qualquer passo, reporte o erro"
# uv run python -m src.main "Busque o post 2 usando o serviço instável, depois busque os comentários desse post, e também busque o usuário 1 em paralelo. Se der erro, reporte o erro"
# uv run python -m src.main "Liste os posts do usuário 1 e verifique tem algum post. Se tiver, reporte o erro, se nao tiver crie um novo post com a mensagem 'bom dia'"
# uv run python -m src.main "obtenha o usuario 3 e valide se o nome dele é 'felipe oliveira' e se ele tem algum post. Se sim, reporte o erro e crie um post com a mensagem 'infelizmente tem post ja para o felipe', se nao crie um novo post com a mensagem 'bom dia' e reporte o sucesso"

# ---------------------------------------------------------------------------
# AI Insight Examples
# ---------------------------------------------------------------------------

# Simple: fetch posts from user 1 and generate an insight about their themes
# uv run python -m src.main "Busque os posts do usuário 1 e gere um resumo dos principais temas abordados nos posts"

# Complex: fetch user 3, their posts and todos in parallel, then generate an insight crossing all data
# uv run python -m src.main "Busque o usuário 3, liste os posts e os todos dele em paralelo, e depois gere uma percepção cruzando todas essas informações — analise a produtividade do usuário comparando a quantidade de posts com a taxa de conclusão dos todos"