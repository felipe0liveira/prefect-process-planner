import httpx
from prefect import task

BASE_URL = "https://jsonplaceholder.typicode.com"


@task(name="get_posts", retries=2, retry_delay_seconds=5)
def get_posts(user_id: int | None = None) -> list[dict]:
    """List posts, optionally filtered by user ID."""
    params = {}
    if user_id is not None:
        params["userId"] = user_id
    response = httpx.get(f"{BASE_URL}/posts", params=params)
    response.raise_for_status()
    return response.json()


@task(name="get_post", retries=2, retry_delay_seconds=5)
def get_post(post_id: int) -> dict:
    """Get a single post by ID."""
    response = httpx.get(f"{BASE_URL}/posts/{post_id}")
    response.raise_for_status()
    return response.json()


@task(name="get_comments", retries=2, retry_delay_seconds=5)
def get_comments(post_id: int) -> list[dict]:
    """List comments for a given post."""
    response = httpx.get(f"{BASE_URL}/posts/{post_id}/comments")
    response.raise_for_status()
    return response.json()


@task(name="get_users", retries=2, retry_delay_seconds=5)
def get_users() -> list[dict]:
    """List all users."""
    response = httpx.get(f"{BASE_URL}/users")
    response.raise_for_status()
    return response.json()


@task(name="get_user", retries=2, retry_delay_seconds=5)
def get_user(user_id: int) -> dict:
    """Get a single user by ID."""
    response = httpx.get(f"{BASE_URL}/users/{user_id}")
    response.raise_for_status()
    return response.json()


@task(name="create_post", retries=2, retry_delay_seconds=5)
def create_post(title: str, body: str, user_id: int) -> dict:
    """Create a new post."""
    payload = {"title": title, "body": body, "userId": user_id}
    response = httpx.post(f"{BASE_URL}/posts", json=payload)
    response.raise_for_status()
    return response.json()


@task(name="get_todos", retries=2, retry_delay_seconds=5)
def get_todos(user_id: int | None = None) -> list[dict]:
    """List todos, optionally filtered by user ID."""
    params = {}
    if user_id is not None:
        params["userId"] = user_id
    response = httpx.get(f"{BASE_URL}/todos", params=params)
    response.raise_for_status()
    return response.json()


@task(name="unreliable_get_post", retries=0)
def unreliable_get_post(post_id: int) -> dict:
    """Get a post by ID, but fails on even IDs to simulate an unstable service."""
    if post_id % 2 == 0:
        raise RuntimeError(
            f"Simulated failure: service unavailable for post {post_id}"
        )
    response = httpx.get(f"{BASE_URL}/posts/{post_id}")
    response.raise_for_status()
    return response.json()


