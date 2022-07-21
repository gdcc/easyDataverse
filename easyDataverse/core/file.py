import os

from typing import Optional
from pydantic import BaseModel, validator

class File(BaseModel):

    filename: str
    description: Optional[str] = None
    file_pid: Optional[str] = None
    local_path: Optional[str] = None

    @validator("description")
    def handle_empty_descriptions(cls, desc):
        """Sets a 'None' description to an empty string"""

        if desc is None:
            return ""
        
        return desc