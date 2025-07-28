"""SDK Agents module.

The SDK layer should only contain general-purpose agent utilities and base classes.
Use-case specific agents belong in their respective use case directories.

For example:
- General agent utilities: ice_sdk.agents.utils
- FB Marketplace agents: use_cases.RivaRidge.FB_Marketplace_Seller.agents
- Other domain agents: use_cases.{Domain}.{UseCase}.agents
"""

# Import only general utilities, not specific agent implementations
from . import utils

__all__ = [
    "utils",
]
