"""Run with `python -m app.worker`. Safe to run multiple processes against PostgreSQL."""

import logging
import signal
import time

from .config import settings
from .services.reports import process_one


def main():
    settings.validate()
    logging.basicConfig(level=logging.INFO)
    running = True

    def stop(*_):
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    while running:
        try:
            if not process_one():
                time.sleep(1)
        except Exception:
            logging.getLogger(__name__).exception("Worker iteration failed")
            time.sleep(3)


if __name__ == "__main__":
    main()
