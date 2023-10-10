import datetime
import logging
import traceback

from services.relief_web_service import ReliefWebService

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def run(event, context):
    #  code to process pdf document
    try:
        current_time = datetime.datetime.now().time()
        name = context.function_name
        logger.info("Your cron function " + name + " ran at " + str(current_time))
        ReliefWebService.scrap_week_data()
    except Exception:
        logger.error(traceback.format_exc())
