#!/usr/bin/env python3
"""Start RQ worker for CTH scan queue."""

import logging
import sys
from pathlib import Path

# Ensure repo root is on sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from redis import Redis
from rq import Worker

from scanner.config import REDIS_URL, RQ_QUEUE_NAME

logging.basicConfig(level=logging.INFO)


def main():
    redis_conn = Redis.from_url(REDIS_URL)
    worker = Worker([RQ_QUEUE_NAME], connection=redis_conn)
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()
