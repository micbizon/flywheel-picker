import logging

logger = logging.getLogger(__name__)


def fetch_insider_buys(days_back: int = 30) -> list[str]:
    logger.warning("insider_buying: OpenInsider niedostępny — źródło tymczasowo wyłączone, zwracam pustą listę")
    return []
