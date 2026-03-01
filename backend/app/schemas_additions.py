from pydantic import BaseModel, EmailStr, constr
from typing import Dict, List, Optional

class SetupStatus(BaseModel):
    completed: bool
    steps_done: List[str]

class SetupCompleteRequest(BaseModel):
    settings: Dict[str, str]
    admin_email: EmailStr
    admin_password: constr(min_length=8)
    admin_name: str
