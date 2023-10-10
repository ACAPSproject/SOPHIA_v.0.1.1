import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv()

# AWS resources
AWS_REGION = "eu-central-1"
RESOURCES_URL_PREFIX: str = os.environ.get("RESOURCES_URL_PREFIX")
RDS_CONNECTION_URL = os.environ.get("RDS_CONNECTION_URL")
SEND_EMAIL_TOPIC = os.environ.get("SEND_EMAIL_TOPIC")

# DB connection
DATABASE_DRIVER = os.environ.get("POSTGRES_DRIVER", "postgresql")
POSTGRES_DB_URL = f"{DATABASE_DRIVER}://{RDS_CONNECTION_URL}"

# ML config
PREDICTION_ENDPOINT_NAME = "multimodel"
MODEL_NAME = "multimodel"
ENDPOINT_CONFIG_NAME = "multimodel-endpoint-config"
# ENDPOINT_NAME = "multimodel2"

# Airtable conection
AIR_TABLE_API_KEY = os.environ.get("AIR_TABLE_API_KEY")
AIR_TABLE_APP_ID = os.environ.get("AIR_TABLE_APP_ID")
