import json
from datetime import datetime, timedelta, timezone

import requests

import logging
from infrastructure.aws import send_to_sqs, send_email
from infrastructure.db import Session
from models.document import Document
from services.air_table_service import AirTableService

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ReliefWebService:
    URL = "https://api.reliefweb.int/v1/reports?appname=ACAPS_scraper"
    DEFAULT_RETRIEVED_DAYS = 1
    PARSE_COMPLETED_NOTIFICATION_SQS_QUEUE = "processing-documents"

    @classmethod
    def scrap_week_data(cls):
        retrieve_data_from = (
            (datetime.now(tz=timezone.utc) - timedelta(days=cls.DEFAULT_RETRIEVED_DAYS))
            .replace(microsecond=0)
            .isoformat()
        )
        iso3_countries = AirTableService.get_iso3()
        iso3_countries = iso3_countries  # + ["wld"]

        relief_web_json = cls._get_data(retrieve_data_from, iso3_countries)
        session = Session()
        num_relief_web_doc = len(relief_web_json)
        for doc in relief_web_json:
            doc_info = doc.get("fields")
            new_doc = Document(
                source_name=doc_info.get("source")[0].get("name"),
                format=doc_info.get("format")[0].get("name"),
                date_relief_web=doc_info.get("date").get("created"),
                date_published=doc_info.get("date").get("original"),
                source_link=doc_info.get("origin"),
                document_text=doc_info.get("body"),
                relief_web_link=doc_info.get("url_alias"),
                attachment_link=doc_info.get("file")[0].get("url") if doc_info.get("file") else "",
                date_downloaded=datetime.now(tz=timezone.utc),
                language=doc_info.get("language")[0].get("name") if doc_info.get("language") else "",
                iso3_multiple=[i.get("iso3") for i in doc_info.get("country", [])],
                disaster_type=[i.get("name") for i in doc_info.get("disaster_type", [])],
                disaster_name=[i.get("name") for i in doc_info.get("disaster", [])],
                disaster_glide_code=[i.get("glide") for i in doc_info.get("disaster", [])],
                theme_relief_web=[i.get("name") for i in doc_info.get("theme", [])],
                title=doc_info.get("title"),
                translated=False,
                processed=False,
                language_iso3=doc_info.get("language")[0].get("code") if doc_info.get("language") else "",
                synchronized=False,
                iso3=doc_info.get("primary_country").get("iso3"),
            )
            session.add(new_doc)

        session.commit()
        send_to_sqs(topic_name=cls.PARSE_COMPLETED_NOTIFICATION_SQS_QUEUE, message="Go")
        # return logged info
        message = f"Reliefweb scraper success: {num_relief_web_doc} docs were scraped today."
        logger.info(message)
        send_email(message)

    @classmethod
    def _get_data(cls, date_from, countries_iso3: list) -> list:
        batch_size = 1000
        f = True
        offset = 0
        res_data = []
        while f:
            request_body = cls._generate_request_body(date_from, countries_iso3)
            response = requests.post(cls.URL, data=json.dumps(request_body))

            if response.status_code != 200:
                raise
            else:
                res_data.extend(response.json().get("data", []))

            if response.json().get("totalCount") <= offset + batch_size:
                f = False
            else:
                offset += batch_size
        return res_data

    @staticmethod
    def _generate_request_body(date_from, countries_iso3: list, batch_size: int = 1000, offset: int = 0) -> dict:
        request_body = {
            "limit": batch_size,
            "offset": offset,
            "preset": "latest",
            # "query": {"value": country_iso3, "fields": ["primary_country.iso3"]},
            "filter": {
                "operator": "AND",
                "conditions": [
                    {
                        "field": "date.created",
                        "value": {
                            "from": date_from
                            # "from": "2022-12-27T00:00:00+00:00",
                            # "to": "2023-02-20T00:00:00+00:00"
                        },
                    },
                    {"field": "source.name", "value": "ACAPS", "negate": True},
                    {
                        "field": "primary_country.iso3",
                        "value": countries_iso3,
                        "operator": "OR",
                    },
                ],
            },
            "fields": {
                "include": [
                    "date.created",
                    "date.original",
                    "origin",
                    "url_alias",
                    "headline.title",
                    "file.url",
                    "primary_country.iso3",
                    "language.name",
                    "language.code",
                    "country.iso3",
                    "disaster.glide",
                    "disaster_type.name",
                    "disaster.name",
                    "source.longname",
                    "source.name",
                    "format.name",
                    "theme.name",
                    "body",
                ]
            },
        }
        return request_body
