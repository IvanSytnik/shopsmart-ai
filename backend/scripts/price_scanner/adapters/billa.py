"""Billa: the online shop's product pages and its promotions page."""

from scripts.price_scanner.adapters.base import StoreAdapter


class BillaAdapter(StoreAdapter):
    key = "billa"
    store = "Billa"
    hosts = frozenset({"shop.billa.at"})
    login_pages = ("https://shop.billa.at/",)
    # Paginated (?page=2); the first page holds the current highlights.
    offer_pages = ("https://shop.billa.at/aktionen",)
    hints = (
        "Billa: 'Immer clever Preis' is a permanent price, so it is the regular price, not "
        "a promotion. Prices for Jö Bonus Club members ('mit Jö', Jö Äpp), discount "
        "stickers to redeem (Rabattsticker, Pickerl) and multi-buy deals are conditional."
    )
