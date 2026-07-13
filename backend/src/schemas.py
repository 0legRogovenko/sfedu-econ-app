from pydantic import BaseModel, ConfigDict


class GroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course: int
    number: str
    subgroup_count: int
