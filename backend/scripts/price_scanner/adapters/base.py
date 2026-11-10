"""A store adapter: which pages to read for one store, and how the model should read them.

Pages are read whole (their text, or a screenshot) and the model finds the prices, so an
adapter needs no CSS selectors that break with every redesign; only its URLs and reading
hints are store-specific.
"""

import logging
from collections.abc import Sequence
from pathlib import Path
from typing import ClassVar
from urllib.parse import urlparse

from scripts.price_scanner.browser import BrowserSession
from scripts.price_scanner.capture import Capture, load_files
from scripts.price_scanner.config import HttpStatusError, ScannerError
from scripts.price_scanner.schemas import Failure, StoreProduct

logger = logging.getLogger(__name__)


class StoreAdapter:
    key: ClassVar[str]  # --store value
    store: ClassVar[str]  # `store` column of catalog_at.csv
    # Product pages (each row's source_url) are read only on these hosts.
    hosts: ClassVar[frozenset[str]]
    # Opened by --login, to accept cookies, log in and pick a PLZ.
    login_pages: ClassVar[tuple[str, ...]]
    # Read after the product pages: current promotions, also of products not in the
    # catalog (they go to review).
    offer_pages: ClassVar[tuple[str, ...]]
    # Store-specific reading rules, added to the model's instructions.
    hints: ClassVar[str]

    def product_pages(self, products: Sequence[StoreProduct]) -> list[str]:
        urls = (p.source_url for p in products if urlparse(p.source_url).hostname in self.hosts)
        return list(dict.fromkeys(urls))

    def pages(self, products: Sequence[StoreProduct]) -> list[str]:
        return [*self.product_pages(products), *self.offer_pages]

    async def scan(
        self, session: BrowserSession, products: Sequence[StoreProduct]
    ) -> tuple[list[Capture], list[Failure]]:
        """Read every product page and offer page; a page that fails is skipped."""
        captures: list[Capture] = []
        failures: list[Failure] = []
        pages = self.pages(products)
        for number, url in enumerate(pages, start=1):
            logger.info("%s %d/%d: %s", self.store, number, len(pages), url)
            try:
                captures.append(await session.capture(url))
            except ScannerError as e:
                logger.warning("  skipped: %s", e)
                status = e.status if isinstance(e, HttpStatusError) else None
                failures.append(Failure(source=url, problem=str(e), http_status=status))
        return captures, failures

    def read_files(self, paths: Sequence[Path]) -> list[Capture]:
        """Flyer pages (images, PDF) or saved page text instead of the browser."""
        return load_files(paths)
