import logging
import traceback

from infrastructure.aws import delete_ml_endpoint

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def run(event, context):
    try:
        delete_ml_endpoint()
    except Exception:
        logger.error(traceback.format_exc())
