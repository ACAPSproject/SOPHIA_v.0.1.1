<!--
title: 'AWS Python Scheduled Cron example in Python'
description: 'This is an example of creating a function that runs as a cron job using the serverless ''schedule'' event.'
layout: Doc
framework: v3
platform: AWS
language: Python
priority: 2
authorLink: 'https://github.com/rupakg'
authorName: 'Rupak Ganguly'
authorAvatar: 'https://avatars0.githubusercontent.com/u/8188?v=4&s=140'
-->
# The Solution Platform for Humanitarian Information Analysis (SOPHIA)

The Solutions Platform for Humanitarian Information Analysis, or SOPHIA, is a suite of services that aim to support data collection and humanitarian information analysis. The system is supported by [ACAPS](https://www.acaps.org/en/). 

This repository hosts code and supplemental documentation for current version of SOPHIA, which allows users to interact with the [UN OCHA ReliefWeb platform](https://reliefweb.int/). This version is a first iteration in product development, supporting limited functionality.

While the SOPHIA platform is delivered through AirTable, the project can easily be modified to deliver its output as a JSON response to your preferred location.

## Setting up environment variables and requirements

- AWS: To develop using this repository, you must set up your environment variable according to the `config.py` file after installing the AWS CLI and your AWS credentials on your system ([AWS CLI documentation](https://aws.amazon.com/cli/)) 

- Serverless: Sophia uses a serverless architecture and the [Serverless Framework](https://www.serverless.com/framework/docs). To change Serverless configurations, change the settings in `serverless.yml` file.

- AirTable API: SOPHIA delivers data to AirTable for ACAPS’ needs. To use the API and generate your API key, please follow the instructions in the [AirTable documentation](https://airtable.com/developers/web/api/introduction). 

## Serverless Framework Python Scheduled Cron on AWS

This template demonstrates how to develop and deploy a simple cron-like service running on AWS Lambda using the traditional Serverless Framework.

### Schedule event type

This examples defines two functions, `rateHandler` and `cronHandler`, both of which are triggered by an event of `schedule` type, which is used for configuring functions to be executed at specific time or in specific intervals. For detailed information about `schedule` event, please refer to corresponding section of Serverless [docs](https://serverless.com/framework/docs/providers/aws/events/schedule/).

When defining `schedule` events, we need to use `rate` or `cron` expression syntax.

#### Rate expressions syntax

```pseudo
rate(value unit)
```

`value` - A positive number

`unit` - The unit of time. ( minute | minutes | hour | hours | day | days )

In below example, we use `rate` syntax to define `schedule` event that will trigger our `rateHandler` function every minute

```yml
functions:
  rateHandler:
    handler: handler.run
    events:
      - schedule: rate(1 minute)
```

Detailed information about rate expressions is available in official [AWS docs](https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/ScheduledEvents.html#RateExpressions).


#### Cron expressions syntax

```pseudo
cron(Minutes Hours Day-of-month Month Day-of-week Year)
```

All fields are required and time zone is UTC only.

| Field         | Values         | Wildcards     |
| ------------- |:--------------:|:-------------:|
| Minutes       | 0-59           | , - * /       |
| Hours         | 0-23           | , - * /       |
| Day-of-month  | 1-31           | , - * ? / L W |
| Month         | 1-12 or JAN-DEC| , - * /       |
| Day-of-week   | 1-7 or SUN-SAT | , - * ? / L # |
| Year          | 192199      | , - * /       |

In below example, we use `cron` syntax to define `schedule` event that will trigger our `cronHandler` function every second minute every Monday through Friday

```yml
functions:
  cronHandler:
    handler: handler.run
    events:
      - schedule: cron(0/2 * ? * MON-FRI *)
```

Detailed information about cron expressions in available in official [AWS docs](https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/ScheduledEvents.html#CronExpressions).


### Usage

#### Deployment

This example is made to work with the Serverless Framework dashboard, which includes advanced features such as CI/CD, monitoring, metrics, etc.

In order to deploy with dashboard, you need to first login with:

```
serverless login
```

and then perform deployment with:

```
serverless deploy
```

After running deploy, you should see output similar to:

```bash
Deploying aws-python-scheduled-cron-project to stage dev (us-east-1)

✔ Service deployed to stack aws-python-scheduled-cron-project-dev (205s)

functions:
  rateHandler: aws-python-scheduled-cron-project-dev-rateHandler (2.9 kB)
  cronHandler: aws-python-scheduled-cron-project-dev-cronHandler (2.9 kB)
```

There is no additional step required. Your defined schedules becomes active right away after deployment.

#### Local invocation

In order to test out your functions locally, you can invoke them with the following command:

```
serverless invoke local --function rateHandler
```

After invocation, you should see output similar to:

```bash
INFO:handler:Your cron function aws-python-scheduled-cron-dev-rateHandler ran at 15:02:43.203145
```

#### Bundling dependencies

In case you would like to include 3rd party dependencies, you will need to use a plugin called `serverless-python-requirements`. You can set it up by running the following command:

```bash
serverless plugin install -n serverless-python-requirements
```

Running the above will automatically add `serverless-python-requirements` to `plugins` section in your `serverless.yml` file and add it as a `devDependency` to `package.json` file. The `package.json` file will be automatically created if it doesn't exist beforehand. Now you will be able to add your dependencies to `requirements.txt` file (`Pipfile` and `pyproject.toml` is also supported but requires additional configuration) and they will be automatically injected to Lambda package during build process. For more details about the plugin's configuration, please refer to [official documentation](https://github.com/UnitedIncome/serverless-python-requirements).

## Version

- V 0.1.1 (release date): This version of SOPHIA collects daily reports published on Reliefweb, translates titles, summary and pdfs to English, splits the text into sentences and sends these sentences to a machine learning model for classification according to ACAPS’ definition of [Humanitarian Access](https://www.acaps.org/en/thematics/all-topics/humanitarian-access), [Protection](https://www.acaps.org/fileadmin/Dataset/Codebook/20230227_acaps_dataset_protection_indicators_codebook.pdf), [Seasonal](https://www.acaps.org/en/thematics/all-topics/seasonal-calendar) and [Information Landscape](https://data.humdata.org/dataset/acaps-information-landscape-dataset) humanitarian frameworks. The resulting classification is then sent to AirTable. 

## Contribution

If you wish to contribute to this project, please fork the repository and submit a pull request from your branch.