import sqlalchemy
from sqlalchemy import Column
from sqlalchemy import String, Integer, Boolean, DateTime
from sqlalchemy.dialects.postgresql import ARRAY

from infrastructure.db import Base

metadata = sqlalchemy.MetaData()


class Document(Base):  # type: ignore
    __tablename__ = "documents"

    id = Column("RecordID", Integer, primary_key=True, autoincrement=True)
    iso3 = Column("ISO3", String)  # , ForeignKey("countries.ISO3"))
    source_name = Column("SourceName", String)
    format = Column("DocumentFormat", String)
    date_relief_web = Column("DateReliefWeb", DateTime)
    date_published = Column("DatePublished", DateTime)
    source_link = Column("SourceLink", String)
    relief_web_link = Column("ReliefWebLink", String)
    attachment_link = Column("AttachmentLink", String)
    date_downloaded = Column("DateDownloaded", DateTime)
    language = Column("Language", String)
    iso3_multiple = Column("ISO3Multiple", ARRAY(String))  # type: ignore
    disaster_type = Column("DisasterType", ARRAY(String))  # type: ignore
    disaster_name = Column("DisasterName", ARRAY(String))  # type: ignore
    disaster_glide_code = Column("DisasterGlideCode", ARRAY(String))  # type: ignore
    theme_relief_web = Column("ThemeReliefWeb", ARRAY(String))  # type: ignore
    title = Column("Title", String)
    document_text = Column("DocumentText", String)
    model_classification = Column("ModelClassification", String)
    date_classified = Column("DateClassified", DateTime)
    translated = Column("Translated", Boolean)
    title_translated = Column("TitleTranslated", String)
    text_translated = Column("TextTranslated", String)
    modified_pdf_link = Column("ModifiedPDFLink", String)
    language_iso3 = Column("LanguageISO3", String)
    processed = Column("Processed", Boolean)
    synchronized = Column("Synchronized", Boolean)
    failed = Column("Failed", Boolean, default=False)


# class Snippet(Base):  # type: ignore
#     __tablename__ = "text_snippets"
#
#     id = Column("SnippetID", Integer, Identity(start=1), primary_key=True)
#     record_id = Column("RecordID", Integer, ForeignKey("documents.RecordID"))
#     snippet_text = Column("SnippetText", String)
#     snippet_classification = Column("SnippetClassification", ARRAY(String))  # type: ignore
#     date_classified = Column("DateClassified", DateTime)
#
#
# class Box(Base):  # type: ignore
#     __tablename__ = "pdf_boxes"
#
#     box_id = Column("BoxID", Integer, Identity(start=1), primary_key=True)
#     snippet_id = Column("SnippetID", Integer, ForeignKey("text_snippets.SnippetID"))
#     page = Column("Page", Integer)
#     location = Column("Location", ARRAY(Integer))  # type: ignore
