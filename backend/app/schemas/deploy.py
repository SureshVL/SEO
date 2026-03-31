from pydantic import BaseModel, Field


class DeployRequest(BaseModel):
    project_id: str = Field(min_length=1)
    platform: str = Field(description="wordpress|shopify|appstore")
    dry_run: bool = True


class DeployResponse(BaseModel):
    platform: str
    status: str
    actions: list[str]
