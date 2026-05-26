"""
Utility functions for KIS Trading Bot
"""

from loguru import logger
import sys

import config


# ==============================================
# Exchange Code Normalizer
# ==============================================

EXCHANGE_MAP = {
    # API response codes -> Order codes
    "NAS": "NASD",
    "NYS": "NYSE",
    "AMS": "AMEX",
    # Already correct codes (passthrough)
    "NASD": "NASD",
    "NYSE": "NYSE",
    "AMEX": "AMEX",
    # Common variations
    "NASDAQ": "NASD",
    "NYSEARCA": "NYSE",
}


def normalize_exchange(exchange_code: str) -> str:
    """Convert API exchange code to order-compatible code
    
    KIS API returns 3-letter codes (NAS, NYS, AMS) in queries,
    but orders require 4-letter codes (NASD, NYSE, AMEX).
    
    Args:
        exchange_code: Exchange code from API response
        
    Returns:
        str: Normalized exchange code for orders
        
    Examples:
        >>> normalize_exchange("NAS")
        'NASD'
        >>> normalize_exchange("NYSE")
        'NYSE'
    """
    if not exchange_code:
        return config.DEFAULT_EXCHANGE
    
    normalized = EXCHANGE_MAP.get(exchange_code.upper())
    
    if normalized is None:
        logger.warning("Unknown exchange code '{}', defaulting to {}", 
                      exchange_code, config.DEFAULT_EXCHANGE)
        return config.DEFAULT_EXCHANGE
    
    return normalized


def get_exchange_for_symbol(symbol: str) -> str:
    """Get the exchange code for a known symbol
    
    Args:
        symbol: Stock ticker symbol
        
    Returns:
        str: Exchange code (NASD, NYSE, or AMEX)
    """
    # Major NASDAQ stocks
    nasdaq_stocks = {"AAPL", "MSFT", "TSLA", "NVDA", "AMD", "GOOGL", "AMZN", "META"}
    
    # Major NYSE stocks
    nyse_stocks = {"JPM", "V", "JNJ", "WMT", "PG", "UNH", "HD", "BAC"}
    
    if symbol.upper() in nasdaq_stocks:
        return "NASD"
    elif symbol.upper() in nyse_stocks:
        return "NYSE"
    else:
        return config.DEFAULT_EXCHANGE


# ==============================================
# Logging Setup
# ==============================================

def setup_logging():
    """Configure loguru for the trading bot"""
    # Remove default handler
    logger.remove()
    
    # Console output with colors
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
               "<level>{message}</level>",
        level=config.LOG_LEVEL,
        colorize=True
    )
    
    # File output
    logger.add(
        config.LOG_FILE,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        level="DEBUG",
        rotation="10 MB",
        retention="30 days",
        compression="zip"
    )
    
    logger.info("Logging initialized (level={})", config.LOG_LEVEL)


# ==============================================
# Price Formatting
# ==============================================

def format_price(price: float, currency: str = "USD") -> str:
    """Format price for display
    
    Args:
        price: Price value
        currency: Currency code
        
    Returns:
        str: Formatted price string
    """
    if currency == "USD":
        return f"${price:,.2f}"
    elif currency == "KRW":
        return f"₩{price:,.0f}"
    else:
        return f"{price:,.2f} {currency}"


def format_percent(value: float) -> str:
    """Format percentage for display
    
    Args:
        value: Decimal value (e.g., 0.05 for 5%)
        
    Returns:
        str: Formatted percentage string
    """
    pct = value * 100
    sign = "+" if pct > 0 else ""
    return f"{sign}{pct:.2f}%"


# ==============================================
# Validation
# ==============================================

def validate_config() -> bool:
    """Validate required configuration values
    
    Returns:
        bool: True if all required values are set
    """
    required = [
        ("KIS_APP_KEY", config.KIS_APP_KEY),
        ("KIS_APP_SECRET", config.KIS_APP_SECRET),
        ("KIS_CANO", config.KIS_CANO),
    ]
    
    missing = []
    for name, value in required:
        if not value or value.startswith("your_"):
            missing.append(name)
    
    if missing:
        logger.error("Missing required config values: {}", missing)
        return False
    
    logger.info("Configuration validated successfully")
    return True


if __name__ == "__main__":
    # Test utilities
    print("Testing Exchange Normalizer:")
    test_codes = ["NAS", "NYS", "AMS", "NASD", "NYSE", "AMEX", "UNKNOWN"]
    for code in test_codes:
        print(f"  {code} -> {normalize_exchange(code)}")
    
    print("\nTesting Symbol Exchange Lookup:")
    test_symbols = ["AAPL", "TSLA", "JPM", "UNKNOWN"]
    for symbol in test_symbols:
        print(f"  {symbol} -> {get_exchange_for_symbol(symbol)}")
    
    print("\nTesting Price Formatting:")
    print(f"  {format_price(123.456)}")
    print(f"  {format_percent(0.0523)}")
    print(f"  {format_percent(-0.0312)}")
