import json
import logging
import traceback

import boto3
from infrastructure.config import (
    RESOURCES_URL_PREFIX,
    PREDICTION_ENDPOINT_NAME,
    MODEL_NAME,
    ENDPOINT_CONFIG_NAME,
    SEND_EMAIL_TOPIC,
)

# Adding a comment for commmit
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

runtime_sm_client = boto3.client(service_name="sagemaker-runtime")
sm_client = boto3.client("sagemaker")


def predict_classes(text, threshold=0.9):
    try:
        # Format the input
        models = [
            "model-Access.tar.gz",
            "model-InformL.tar.gz",
            "model-Protection.tar.gz",
            "model-Seasonal.tar.gz",
        ]
        payload = {"inputs": text, "parameters": {"return_all_scores": True}}
        predicted_classes = []
        # Send text via InvokeEndpoint API
        label_names = [f"tag_{model_name[6:-7]}" for model_name in models]

        for ind, model_name in enumerate(models):
            response = runtime_sm_client.invoke_endpoint(
                EndpointName=PREDICTION_ENDPOINT_NAME,
                ContentType="application/json",
                TargetModel=model_name,
                Body=json.dumps(payload),
            )
            result = json.loads(response["Body"].read().decode())
            predicted_classes.extend(
                [label_names[ind] for item in result[0] if item["score"] >= threshold and item["label"] == 1]
            )

    except Exception:
        logger.error(traceback.format_exc())
        predicted_classes = []

    return predicted_classes


def send_to_sqs(topic_name: str, message: str) -> None:
    sqs = boto3.client("sqs")

    # queue = sqs.get_queue_by_name(QueueName=f"{RESOURCES_URL_PREFIX}{topic_name}")

    sqs.send_message(QueueUrl=f"{RESOURCES_URL_PREFIX}{topic_name}", MessageBody=message)


def get_s3():
    return boto3.client("s3")


def get_translation_service():
    return boto3.client("translate")


def create_ml_endpoint():
    # create endpoint config
    response = sm_client.create_endpoint_config(
        EndpointConfigName=ENDPOINT_CONFIG_NAME,
        ProductionVariants=[
            {
                "VariantName": "AllTraffic",
                "ModelName": MODEL_NAME,
                "InitialInstanceCount": 1,
                "InstanceType": "ml.c5.2xlarge",
            }
        ],
    )
    # deploy endpoint
    response = sm_client.create_endpoint(EndpointName=PREDICTION_ENDPOINT_NAME, EndpointConfigName=ENDPOINT_CONFIG_NAME)
    return response


def delete_ml_endpoint():
    endpoint_del = sm_client.delete_endpoint(EndpointName=PREDICTION_ENDPOINT_NAME)
    endpoint_config_del = sm_client.delete_endpoint_config(EndpointConfigName=ENDPOINT_CONFIG_NAME)
    return endpoint_del, endpoint_config_del


def send_email(message: str) -> None:
    sns = boto3.client("sns")
    sns.publish(TopicArn=str(SEND_EMAIL_TOPIC), Message=message)
