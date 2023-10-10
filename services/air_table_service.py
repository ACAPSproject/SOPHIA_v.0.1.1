import logging
from typing import List
import requests

from models.document import Document
from infrastructure.config import AIR_TABLE_API_KEY, AIR_TABLE_APP_ID

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class AirTableService:
    BATCH_MAX_COUNT = 10
    AIR_TABLE_DOCUMENT_URL = f"https://api.airtable.com/v0/{AIR_TABLE_APP_ID}/tblT5ISXLvn7Uy80F"
    AIR_TABLE_ISO3_URL = f"https://api.airtable.com/v0/{AIR_TABLE_APP_ID}/tblPoIADo5pGxyO76"

    @classmethod
    def create_records(cls, documents: List[Document]) -> bool:
        records = []

        for document in documents:
            air_table_rec = {
                "fields": {
                    "RecordID": document.id,
                    "ISO3": document.iso3,
                    "SourceName": document.source_name,
                    "DocumentFormat": document.format,
                    "DateReliefWeb": document.date_relief_web.isoformat() if document.date_relief_web else "",
                    "DatePublished": document.date_published.strftime("%m/%d/%Y") if document.date_published else "",
                    "SourceLink": document.source_link,
                    "ReliefWebLink": document.relief_web_link,
                    "AttachmentLink": document.attachment_link,
                    "DateDownloaded": document.date_downloaded.isoformat() if document.date_downloaded else "",
                    "Language": document.language,
                    "Title": document.title,
                    "DocumentText": document.document_text,
                    "ModelClassification": document.model_classification if not document.failed else "FAILED",
                    "TitleTranslated": document.title_translated,
                    "TextTranslated": document.text_translated,
                    "ModifiedPDFLink": document.modified_pdf_link,
                    "Translated": document.translated,
                    "ISO3Multiple": ", ".join(document.iso3_multiple),
                }
            }
            records.append(air_table_rec)

        request_body = {
            "records": records,
        }
        barer_header = {"Authorization": f"Bearer {AIR_TABLE_API_KEY}"}
        response = requests.post(cls.AIR_TABLE_DOCUMENT_URL, json=request_body, headers=barer_header)
        if response.status_code != 200:
            logger.error(response.__dict__)
            return False
        else:
            logger.info("AirTable was updated")
            return True

    @classmethod
    def get_iso3(cls):
        barer_header = {"Authorization": f"Bearer {AIR_TABLE_API_KEY}"}
        url = cls.AIR_TABLE_ISO3_URL + "?filterByFormula=IF({Data Collector}= BLANK(), 'Skip', 'Monitor')"
        resp = requests.get(url, headers=barer_header)
        if resp.status_code == 200:
            return [i["fields"]["ISO3"].lower() for i in resp.json().get("records", [])]
        else:
            return []
