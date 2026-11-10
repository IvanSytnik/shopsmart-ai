"""Hofer: product pages on hofer.at and the weekly offers page.

Hofer has no online grocery shop of its own; hofer.at lists fresh categories and current
offers with prices (see docs/CATALOG.md). The delivery service Roksh is opened by --login
only, to set a PLZ there for manual checks; scans don't read it.
"""

from scripts.price_scanner.adapters.base import StoreAdapter


class HoferAdapter(StoreAdapter):
    key = "hofer"
    store = "Hofer"
    hosts = frozenset({"www.hofer.at"})
    login_pages = ("https://www.hofer.at/", "https://www.roksh.at/")
    offer_pages = ("https://www.hofer.at/de/angebote.html",)
    hints = (
        "Hofer: 'Preis gesenkt' or 'dauerhaft' marks a new permanent price, so it is the "
        "regular price, not a promotion. Weekly offers are headed by their first day "
        "('ab Montag, 9.11.'): that is promo_valid_from; many have no last day. Leave out "
        "one-off non-grocery offers (clothing, tools, electronics)."
    )
