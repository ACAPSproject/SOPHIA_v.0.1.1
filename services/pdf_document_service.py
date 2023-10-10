import io
import logging
import uuid
from typing import List
from dotenv import load_dotenv

import requests
import fitz
from collections import defaultdict
from sqlalchemy import select, and_
from nltk import download as nltk_download
from nltk import data as nltk_data
from nltk.tokenize import sent_tokenize, word_tokenize

from infrastructure import config
from infrastructure.aws import (
    send_to_sqs,
    get_s3,
    get_translation_service,
    predict_classes,
    send_email,
)
from infrastructure.db import Session
from models.document import Document
from services.air_table_service import AirTableService

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

load_dotenv()


class PDFDocumentService:
    S3_INPUT_BUCKET_NAME = "acaps-sofia-input-pdfs"
    S3_PROCESSED_BUCKET_NAME = "acaps-sofia-output-pdfs"
    PROCESSING_DOCUMENTS_PDF_SQS_QUEUE = "processing-documents-pdf"
    PROCESSING_DOCUMENTS_META_SQS_QUEUE = "processing-documents-meta-data"
    ISO3_ENG = "en"
    TEXT_TRANSLATION_TYPES = ["Infographic", "Map", "Interactive", "Other"]
    DAY_PROCESSING_LIMIT = 150
    MIN_TEXT_BLOCK = 20
    MAX_SNIPED_SIZE = 80

    @classmethod
    def make_tasks_for_processing(cls):
        unprocessed_documents = cls._get_unprocessed_documents()
        logger.info(unprocessed_documents)
        num_doc_to_process = len(unprocessed_documents)
        num_pdf = 0
        num_not_pdf = 0
        for document in unprocessed_documents:
            logger.info(f"doc: {document.id}")
            if document.format in cls.TEXT_TRANSLATION_TYPES or not document.attachment_link:
                send_to_sqs(
                    topic_name=cls.PROCESSING_DOCUMENTS_META_SQS_QUEUE,
                    message=str(document.id),
                )
                num_not_pdf += 1
            else:
                send_to_sqs(
                    topic_name=cls.PROCESSING_DOCUMENTS_PDF_SQS_QUEUE,
                    message=str(document.id),
                )
                num_pdf += 1
        # return log info
        message = (
            f"{num_doc_to_process} documents sent to be processed.\n"
            f"{num_pdf} documents have a pdf. {num_not_pdf} documents do not have a pdf. "
        )
        logger.info(message)
        send_email(message)

    @classmethod
    def _get_unprocessed_documents(cls) -> List[Document]:
        session = Session()
        res = session.execute(select(Document).filter(Document.processed.is_(False)).limit(cls.DAY_PROCESSING_LIMIT))
        return res.scalars().all()

    @staticmethod
    def _get_document_by_id(doc_id: str) -> Document:
        session = Session()
        query = select(Document).filter(Document.id == int(doc_id))
        res = session.execute(query).scalar_one()
        return res

    @classmethod
    def process_document(cls, doc_id: str):
        nltk_data.path.append("/tmp")
        nltk_download("punkt", download_dir="/tmp")
        session = Session()
        doc_name = uuid.uuid4()
        doc = cls._get_document_by_id(doc_id)
        doc.processed = True
        doc.failed = True
        session.add(doc)
        session.commit()

        original_pdf_bytes = requests.get(doc.attachment_link).content
        # cls._put_document_to_s3(original_pdf_bytes, f"{doc_name}.pdf", cls.S3_INPUT_BUCKET_NAME)
        pdf_document = fitz.open("pdf", stream=io.BytesIO(original_pdf_bytes))
        res_pdf_document = fitz.open("pdf", stream=io.BytesIO(original_pdf_bytes))

        aws_translate = get_translation_service()

        gold_color_to_mark = (1, 1, 0)
        doc_stat: dict = defaultdict(lambda: 0)

        p_no = 0
        for page in pdf_document:
            blocks = page.get_text("dict")["blocks"]

            new_page = res_pdf_document.new_page(pno=p_no + 1)
            shape = new_page.new_shape()  # create Shape
            page_tags = []

            for block in blocks:
                if block["type"] == 0:
                    block_text = ""
                    font_size = 11.0

                    for block_line in block["lines"]:
                        line_text = "".join(i["text"] for i in block_line["spans"])
                        block_text += f" {line_text}"
                        block_font_size = block_line["spans"][0]["size"]
                        font_size = block_font_size if 7 < block_font_size < font_size else font_size

                    if doc.language_iso3 != cls.ISO3_ENG and block_text:
                        block_text = cls._translate_text(block_text, doc.language_iso3, aws_translate)

                    if len(word_tokenize(block_text)) > cls.MIN_TEXT_BLOCK:
                        sentences = sent_tokenize(block_text)
                        processed_sent_count = 0
                        sniped = ""
                        while processed_sent_count < len(sentences):
                            cur_sent = sentences[processed_sent_count]
                            if len(word_tokenize(sniped)) + len(word_tokenize(cur_sent)) <= cls.MAX_SNIPED_SIZE:
                                sniped += f" {cur_sent}"
                                processed_sent_count += 1
                            elif not sniped and len(word_tokenize(cur_sent)) > cls.MAX_SNIPED_SIZE:
                                sniped += f" {cur_sent}"
                                processed_sent_count += 1
                            else:
                                new_keys = predict_classes(sniped)
                                if new_keys:
                                    page_tags.append(dict(keys=new_keys, sniped=sniped))
                                sniped = ""

                        if len(word_tokenize(sniped)) >= cls.MIN_TEXT_BLOCK:
                            new_keys = predict_classes(sniped)
                            if new_keys:
                                page_tags.append(dict(keys=new_keys, sniped=sniped))
                            sniped = ""

                    new_rect = fitz.Rect(
                        block["bbox"][0],
                        block["bbox"][1],
                        block["bbox"][2],
                        block["bbox"][3],
                    )
                    shape.draw_rect(new_rect)

                    # if meta_keys:
                    #     shape.finish(color=(1, 1, 1), fill=gold_color_to_mark)
                    # else:
                    shape.finish(color=(1, 1, 1))
                    rc = -1

                    while font_size > 0 and rc < 0:
                        rc = shape.insert_textbox(
                            new_rect,
                            block_text,
                            fontsize=font_size,
                            color=(0, 0, 0),
                            lineheight=1,
                        )
                        font_size -= 0.1

                    for tagged_sniped in page_tags:
                        keys_tag = ""
                        for meta_key in tagged_sniped["keys"]:
                            doc_stat[meta_key] += 1
                            keys_tag += f"#{meta_key}_framework, "
                        place_to_fill = new_page.search_for(tagged_sniped["sniped"])
                        if len(place_to_fill) > 0:
                            tagged_rect = fitz.Rect(
                                place_to_fill[0].x0,
                                place_to_fill[0].y0,
                                place_to_fill[0].x1,
                                place_to_fill[0].y1,
                            )
                            shape.draw_rect(tagged_rect)
                            rc = -1
                            font_size = 10
                            while font_size > 0 and rc < 0:
                                rc = new_page.insert_textbox(
                                    tagged_rect,
                                    keys_tag,
                                    fontsize=font_size,
                                    color=(1, 0, 0),
                                )
                                font_size -= 0.2

                            shape.finish(color=(1, 1, 1), fill=gold_color_to_mark)
                        else:
                            tagged_rect = fitz.Rect(
                                block["bbox"][0],
                                block["bbox"][1],
                                block["bbox"][2],
                                block["bbox"][3],
                            )
                            shape.draw_rect(tagged_rect)
                            rc = -1
                            font_size = 10
                            while font_size > 0 and rc < 0:
                                rc = new_page.insert_textbox(
                                    tagged_rect,
                                    keys_tag,
                                    fontsize=font_size,
                                    color=(1, 0, 0),
                                )
                                font_size -= 0.2
                            shape.finish(color=(1, 1, 1), fill=gold_color_to_mark)
            shape.commit()

            p_no += 2

        s3_link = cls._put_document_to_s3(res_pdf_document.write(), f"{doc_name}.pdf", cls.S3_PROCESSED_BUCKET_NAME)
        doc.modified_pdf_link = s3_link
        if doc.language_iso3 != cls.ISO3_ENG:
            doc.title_translated = cls._translate_text(doc.title, doc.language_iso3, aws_translate)
            if doc.document_text:
                doc.text_translated = cls._translate_text(doc.document_text, doc.language_iso3, aws_translate)
            doc.translated = True
        if doc_stat.items():
            doc.model_classification = ", ".join(f"{key} - {value}" for key, value in doc_stat.items())
        doc.failed = False
        session.add(doc)
        session.commit()

    @classmethod
    def process_body(cls, doc_id: str):
        nltk_data.path.append("/tmp")
        nltk_download("punkt", download_dir="/tmp")

        session = Session()
        doc = cls._get_document_by_id(doc_id)
        doc.processed = True
        doc.failed = True
        session.add(doc)
        session.commit()

        doc_stat: dict = defaultdict(lambda: 0)

        if doc.document_text:
            sentences = sent_tokenize(doc.document_text)
        else:
            sentences = []

        if doc.language_iso3 != cls.ISO3_ENG:
            aws_translate = get_translation_service()
            doc.title_translated = cls._translate_text(doc.title, doc.language_iso3, aws_translate)
            translated_sentences = []
            for sentence in sentences:
                translated_sentences.append(cls._translate_text(sentence, doc.language_iso3, aws_translate))
            sentences = translated_sentences
        processed_sent_count = 0
        sniped = ""
        res = ""
        while processed_sent_count < len(sentences):
            cur_sent = sentences[processed_sent_count]
            if len(word_tokenize(sniped)) + len(word_tokenize(cur_sent)) <= cls.MAX_SNIPED_SIZE:
                sniped += f" {cur_sent}"
                processed_sent_count += 1
            elif not sniped and len(word_tokenize(cur_sent)) > cls.MAX_SNIPED_SIZE:
                sniped += f" {cur_sent}"
                processed_sent_count += 1
            else:
                meta_keys = predict_classes(sniped)
                if meta_keys:
                    keys_tag = ""
                    for meta_key in meta_keys:
                        doc_stat[meta_key] += 1
                        keys_tag += f"#{meta_key}_framework, "
                    res += f"<br>({keys_tag}) {sniped}</br>"
                else:
                    res += f" {sniped}"
                sniped = ""
        if len(word_tokenize(sniped)) >= cls.MIN_TEXT_BLOCK:
            meta_keys = predict_classes(sniped)
            if meta_keys:
                keys_tag = ""
                for meta_key in meta_keys:
                    doc_stat[meta_key] += 1
                    keys_tag += f"#{meta_key}_framework, "
                res += f"<br>({keys_tag}) {sniped}</br>"
            else:
                res += f" {sniped}"
        doc.text_translated = res
        if doc_stat.items():
            doc.model_classification = ", ".join(f"{key} - {value}" for key, value in doc_stat.items())
        if doc.language_iso3 != cls.ISO3_ENG:
            doc.translated = True
        doc.failed = False
        session.add(doc)
        session.commit()

    # @classmethod
    # def upser_example(cls, doc_id: int, s3_link: str):
    #     stmt = insert(Document).values(user_email="a@b.com", data="inserted data")
    #     stmt = stmt.on_conflict_do_update(
    #         index_elements=[Document.c.user_email],
    #         index_where=Document.c.user_email.like("%@gmail.com"),
    #         set_=dict(data=stmt.excluded.data),
    #     )

    @classmethod
    def _put_document_to_s3(cls, content: bytes, doc_title: str, bucket_name: str) -> str:
        s3 = get_s3()
        s3.upload_fileobj(io.BytesIO(content), bucket_name, f"{doc_title}")
        return f"https://{bucket_name}.s3.{config.AWS_REGION}.amazonaws.com/{doc_title}"

    @classmethod
    def _translate_text(cls, text: str, iso3_lang: str = "auto", aws_translate=None):
        if not aws_translate:
            aws_translate = get_translation_service()
        try:
            response = aws_translate.translate_text(
                Text=text,
                TerminologyNames=[],
                SourceLanguageCode="auto",
                TargetLanguageCode=cls.ISO3_ENG,
                Settings={
                    "Formality": "FORMAL",
                    # "Profanity": "MASK"
                },
            )
        except Exception:
            try:
                response = aws_translate.translate_text(
                    Text=text,
                    TerminologyNames=[],
                    SourceLanguageCode=iso3_lang,
                    TargetLanguageCode=cls.ISO3_ENG,
                    Settings={
                        "Formality": "FORMAL",
                        # "Profanity": "MASK"
                    },
                )
            except Exception:
                return "Can't translate the text"
        return response.get("TranslatedText", "")

    @classmethod
    def update_air_table(cls):
        session = Session()
        res = session.execute(
            select(Document).filter(and_(Document.synchronized.is_(False)), Document.processed.is_(True))
        )
        documents = res.scalars().all()
        batch_for_sync = []
        num_sync_airtable = len(documents)
        for document in documents:
            batch_for_sync.append(document)

            if len(batch_for_sync) == AirTableService.BATCH_MAX_COUNT:
                updater_res = AirTableService.create_records(batch_for_sync)

                if updater_res:
                    for synced_doc in batch_for_sync:
                        synced_doc.synchronized = True
                        session.add(synced_doc)
                    session.commit()

                batch_for_sync = []

        if len(batch_for_sync):
            updater_res = AirTableService.create_records(batch_for_sync)
            if updater_res:
                for synced_doc in batch_for_sync:
                    synced_doc.synchronized = True
                    session.add(synced_doc)
                session.commit()
                # return logged info
                message = f"Doc sync to AirTable base: {num_sync_airtable} docs were synced to Airtable."
                logger.info(message)
                send_email(message)
