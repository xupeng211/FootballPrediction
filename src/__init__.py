# Football Prediction System
# Core modules are imported on demand

__version__ = "1.0.0"
__author__ = "Football Prediction Team"

# Minimal imports only
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Type hints only, no runtime imports
    from . import services
    from . import api
    from . import core
    from . import database
    from . import cache
    from . import adapters
