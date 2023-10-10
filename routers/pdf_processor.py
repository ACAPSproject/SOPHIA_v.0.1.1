import logging
import traceback

from services.pdf_document_service import PDFDocumentService

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def run(event, context):
    try:
        for record in event["Records"]:
            PDFDocumentService.process_document(record["body"])
    except Exception:
        logger.error(traceback.format_exc())
