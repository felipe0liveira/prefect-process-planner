from pydantic import BaseModel, field_validator


class Node(BaseModel):
    id: str
    tool: str
    params: dict = {}
    depends_on: list[str] = []
    on_error: str | None = None


class ExecutionPlan(BaseModel):
    description: str
    nodes: list[Node]

    @field_validator("nodes")
    @classmethod
    def validate_nodes(cls, v: list[Node]) -> list[Node]:
        ids = {node.id for node in v}
        if len(ids) != len(v):
            raise ValueError("Node IDs must be unique")
        for node in v:
            for dep in node.depends_on:
                if dep not in ids:
                    raise ValueError(
                        f"Node '{node.id}' depends on '{dep}' which does not exist"
                    )
            if node.on_error and node.on_error not in ids:
                raise ValueError(
                    f"Node '{node.id}' has on_error '{node.on_error}' "
                    f"which does not exist"
                )
        return v

    def fallback_node_ids(self) -> set[str]:
        """Return IDs of nodes that are only used as error fallbacks."""
        return {
            node.on_error for node in self.nodes if node.on_error
        }
