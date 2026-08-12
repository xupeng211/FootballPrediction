"""Network infrastructure package boundary.

The supported NetworkShield implementation is the Node.js module at
``src/infrastructure/network/NetworkShield.js``. The historical Python
NetworkShield exports are intentionally not re-exported: their implementation
is not present in this repository.

Python callers with a supported specialized need import the concrete module,
such as ``src.infrastructure.network.stealth_client``, directly.

lifecycle: permanent
component: package import boundary
"""

__all__: tuple[str, ...] = ()

__version__ = "1.0.0"
__author__ = "[Genesis.NetworkShield]"
