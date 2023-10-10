import logging
import traceback

from infrastructure.aws import create_ml_endpoint

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def run(event, context):
    try:
        create_ml_endpoint()
    except Exception:
        logger.error(traceback.format_exc())
