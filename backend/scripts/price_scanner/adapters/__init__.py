"""Store adapters by --store name."""

from scripts.price_scanner.adapters.base import StoreAdapter
from scripts.price_scanner.adapters.billa import BillaAdapter
from scripts.price_scanner.adapters.hofer import HoferAdapter

ADAPTERS: dict[str, StoreAdapter] = {
    adapter.key: adapter for adapter in (BillaAdapter(), HoferAdapter())
}

# Flyer portals, opened by --login next to the stores: their flyers can be saved as PDF or
# screenshots for --from-files. (Aktionsfinder has been offline since May 2026.)
FLYER_PORTALS = ("https://www.marktguru.at/",)

__all__ = ["ADAPTERS", "FLYER_PORTALS", "StoreAdapter"]
