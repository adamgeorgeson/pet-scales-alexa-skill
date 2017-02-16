import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from datetime import datetime
from flask import Flask, json, render_template
from flask_ask import Ask, request, session, question, statement
# from IPython import embed
import logging
import traceback
import uuid

app = Flask(__name__)
ask = Ask(app, "/")
logging.getLogger('flask_ask').setLevel(logging.DEBUG)

@ask.launch
def launch():
    try:
        welcome_text = render_template('welcome')
        reprompt_text = render_template('welcome_reprompt')
        return question(welcome_text).reprompt(reprompt_text)
    except Exception as e:
        logging.error(e)

@ask.intent('NewFeedIntent')
def create_feed(pet_name, feed_value):
    try:
        if (pet_name is None or feed_value is None):
            return statement(render_template('create_reprompt'))

        if (not feed_value.isdigit()):
            return statement(render_template('create_reprompt_again'))

        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = dynamodb.Table('petFeeds')

        response = table.put_item(
                Item={
                    "uuid": uuid.uuid4().hex,
                    "userId": session.user.userId,
                    "timestamp": str(request.timestamp),
                    "petName": pet_name,
                    "feedValue": int(feed_value),
                    "feedUnit": 'grams'
                    }
                )

        text = render_template('create_successful', petName=pet_name)
        return statement(text)
    except ClientError as e:
        logging.error(e.response['Error'])
        return statement(render_template('unexpected_error'))
    except Exception:
        logging.error(traceback.format_exc())
        return statement(render_template('unexpected_error'))

@ask.intent('DailyTotalIntent')
def get_daily_totals():
    try:
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = dynamodb.Table('petFeeds')

        today = datetime.now()
        today_beginning = today.strftime("%Y-%m-%d 00:00:00")
        today_end = today.strftime("%Y-%m-%d 23:59:59")

        response = table.scan(FilterExpression=Attr('userId').eq(session.user.userId) & Attr('timestamp').between(today_beginning, today_end))

        if (response['Count'] == 0):
            return statement(render_template('get_daily_totals_no_results_found'))

        pet_feed_totals = {}
        for i in response['Items']:
            pet_feed_totals[i['petName']] = pet_feed_totals.get(i['petName'], 0) + int(i['feedValue'])

        result_text = "Today"
        for i in pet_feed_totals:
            result_text += ", " + render_template('get_daily_totals_response', petName=i, dailyTotal=pet_feed_totals[i])

        return statement(result_text)
    except ClientError as e:
        logging.error(e.response['Error'])
        return statement(render_template('unexpected_error'))
    except Exception:
        logging.error(traceback.format_exc())
        return statement(render_template('unexpected_error'))

@ask.intent('AMAZON.HelpIntent')
def help():
    help_text = render_template('help')
    return question(help_text).reprompt(help_text)


@ask.intent('AMAZON.StopIntent')
def stop():
    bye_text = render_template('bye')
    return statement(bye_text)


@ask.intent('AMAZON.CancelIntent')
def cancel():
    bye_text = render_template('bye')
    return statement(bye_text)


@ask.session_ended
def session_ended():
    return "", 200

if __name__ == '__main__':
    app.run(debug=True)
