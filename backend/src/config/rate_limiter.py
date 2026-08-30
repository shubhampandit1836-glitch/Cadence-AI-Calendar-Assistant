from slowapi import Limiter
from slowapi.util import get_remote_address

# Shared Limiter instance — imported by main.py (to register the exception handler)
# and by any route that needs a tighter, endpoint-specific limit.
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])