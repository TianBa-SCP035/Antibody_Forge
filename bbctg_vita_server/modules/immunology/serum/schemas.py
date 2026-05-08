from typing import Any

from pydantic import BaseModel, ConfigDict


class SerumPayload(BaseModel):
    model_config = ConfigDict(extra="allow")


SerumData = dict[str, Any]
