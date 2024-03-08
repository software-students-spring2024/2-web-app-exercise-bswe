# Web Application Exercise

A little exercise to build a web application following an agile development process. See the [instructions](instructions.md) for more detail.

## Product vision statement

To simplify shared financial experiences by turning the often stressful task of bill splitting into a seamless, positive experience.

## User stories

[Link To User Stories](https://github.com/software-students-spring2024/2-web-app-exercise-bswe/issues)

## Task boards

[Link To Taskboards](https://github.com/orgs/software-students-spring2024/projects/9)

## Project Overview

The goal of Checkmate is to turn the experience of picking up the check from a chore to an easy win as the best friend in the friend group. The vision is to have a seamless process where Checkmate takes you from a photo of your receipt to an automated payment request feature in seconds. The app stores your payment information and your friends' contact information. When you get the check, you take a picture, the optical character recognition (OCR) algorithm scans the receipt, logs the relevant information, and creates a digital copy. The user corrects any errors, if any, and splits the bill/individual items between stored contacts. Optionally, there is an element of fun where friends can decide to gamble who pays the bill. Checkmate would then use stored contact information and payment details to notify and remind friends to pay you back.

Ultimately we fell short of our vision due to underestimating our given scope. We were not able to reach all of our goals and complete all of our user stories. Notably, OCR and notifications were out of the scope of this project given time restraints and prior knowledge. However, we still learned a lot about flask and pymongo from building out our basic, working prototype. 

## Setup Instructions (Based on resources from Amos Bloomberg)

3 steps to set up local hosting:

1. docker build -t ebc5802/2-web-app-exercise-bswe .

2. docker run --name mongodb_dockerhub -p 27017:27017 -e MONGO_INITDB_ROOT_USERNAME=admin -e MONGO_INITDB_ROOT_PASSWORD=secret -d mongo:latest

3. docker run -ti --rm -d -p 10000:5000 -e MONGO_DBNAME=bswe_db -e MONGO_URI="mongodb://admin:secret@host.docker.internal:27017" ebc5802/2-web-app-exercise-bswe

### Create a `.env` file

A file named `.env` is necessary to run the application. This file contains sensitive environment variables holding credentials such as the database connection string, username, password, etc. This file should be excluded from version control in the [`.gitignore`](.gitignore) file.

### Run the app

- define two environment variables from the command line:
  - on Mac, use the commands: `export FLASK_APP=app.py` and `export FLASK_ENV=development`.
  - on Windows, use `set FLASK_APP=app.py` and `set FLASK_ENV=development`.
- start flask with `flask run` - this will output an address at which the app is running locally, e.g. https://127.0.0.1:5000. Visit that address in a web browser.
- in some cases, the command `flask` will not be found when attempting `flask run`... you can alternatively launch it with `python3 -m flask run --host=0.0.0.0 --port=5000` (or change to `python -m ...` if the `python3` command is not found on your system).

Note that this will run the app only on your own computer. Other people will not be able to access it. If you want to allow others to access the app running on your local machine, try using the [flask-ngrok](https://pypi.org/project/flask-ngrok/) module.