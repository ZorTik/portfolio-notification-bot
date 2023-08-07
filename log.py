import logging
import sys


def setup_handler(handler: logging.Handler):
    formatter = logging.Formatter("[%(name)s] %(levelname)s > %(message)s")
    handler.setFormatter(formatter)
    return handler


logger = logging.getLogger("portfolio_bot")
logger.addHandler(setup_handler(logging.StreamHandler(sys.stdout)))
logger.setLevel(logging.INFO)
