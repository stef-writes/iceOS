from typing import List, Optional
from pydantic import BaseModel


class User(BaseModel):
    """User model for permission checking"""
    id: str
    roles: List[str]
    
    def has_role(self, role: str) -> bool:
        """Check if user has specific role"""
        return role in self.roles


class Chain(BaseModel):
    """Chain model for permission validation"""
    id: str
    name: str
    is_demo: bool = False


def validate_chain_permissions(chain: Chain, user: User) -> bool:
    """Pre-execution check for demo chains"""
    if chain.id.endswith("_demo") or chain.is_demo:
        return user.has_role("demo_user")
    return True