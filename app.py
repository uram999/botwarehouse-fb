# -*- coding: utf-8 -*-
import os
import sys
import json
from datetime import datetime

import requests
from flask import Flask, request

app = Flask(__name__)

@app.route('/', methods=['GET'])
def verify():
    # when the endpoint is registered as a webhook, it must echo back
    # the 'hub.challenge' value it receives in the query arguments
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == os.environ["VERIFY_TOKEN"]:
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200

    return "Hello world", 200


@app.route('/', methods=['POST'])
def webhook():

    # endpoint for processing incoming messaging events

    data = request.get_json()
    log(data)  # you may not want to log every incoming message in production, but it's good for testing

    if data["object"] == "page":

        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:

                if messaging_event.get("message"):  # someone sent us a message

                    sender_id = messaging_event["sender"]["id"]        # the facebook ID of the person sending you the message
                    recipient_id = messaging_event["recipient"]["id"]  # the recipient's ID, which should be your page's facebook ID
                    message_text = messaging_event["message"]["text"]  # the message's text
                    print(message_text)

                    send_message(sender_id, "roger that!")

                if messaging_event.get("delivery"):  # delivery confirmation
                    pass

                if messaging_event.get("optin"):  # optin confirmation
                    pass

                if messaging_event.get("postback"):  # user clicked/tapped "postback" button in earlier message
                    sender_id = messaging_event["sender"]["id"]
                    postback = messaging_event["postback"]["payload"]

                    if postback == "INFO_PLAYLOAD":
                        send_message(sender_id, "========= 사 용 방 법 ========= ")
                        send_message(sender_id, "1. 설명 보기 : 사용 방법을 볼 수 있다.")
                        send_message(sender_id, "2. 내 관심종목 : 등록된 내 관심종목을 보여줍니다")
                        send_message(sender_id, "3. 지표 보기 : 등록된 관심종목의 매수/매도 지표를 보여줍니다")

                    elif postback == "LIST_PAYLOAD":
                        generic_info = get_list_info(sender_id)
                        send_message(sender_id, "등록되어 있는 관심 종목들을 알려드릴게요!")
                        for info in generic_info:
                            send_message(sender_id, "{name} ({code}) - {busiType}"
                                         .format(name=info['stock_name'], code=info['stock_code'], busiType=info['stock_busiType']))

                    elif postback == "POINT_PLAYLOAD":
                        send_message(sender_id, "관심 종목의 지표를 알려드릴게요!")
                    pass

    return "ok", 200


def get_list_info(recipient_id):
    URL = os.environ["SERVER_URL"] + '/stock/get_stock_list?user_id=uram999'
    response = requests.get(URL)

    data = json.loads(response.text)
    return data
    # generic_info = json.dumps({
    #     "attachment": {
    #         "type": "template",
    #         "payload": {
    #             "template_type": "generic",
    #             "elements": [{
    #                 "title": data[0]['stock_name']+"("+data[0]['stock_code']+")",
    #                 "image_url": "https://petersfancybrownhats.com/company_image.png",
    #                 "subtitle": data[0]['stock_busiType'],
    #                 "default_action":  {
    #                     "type": "web_url",
    #                     "url": "https://petersfancybrownhats.com/view?item=103",
    #                     "messenger_extensions": False,
    #                     "webview_height_ratio": "tall",
    #                     "fallback_url": "https://petersfancybrownhats.com/"
    #                 },
    #                 "buttons": [{
    #                     "type": "postback",
    #                     "title": "Start Chatting",
    #                     "payload": "DEVELOPER_DEFINED_PAYLOAD"
    #                 }]
    #             },  {
    #                 "title": data[1]['stock_name']+"("+data[1]['stock_code']+")",
    #                 "image_url": "https://petersfancybrownhats.com/company_image.png",
    #                 "subtitle": data[1]['stock_busiType'],
    #                 "default_action":  {
    #                     "type": "web_url",
    #                     "url": "https://petersfancybrownhats.com/view?item=103",
    #                     "messenger_extensions": False,
    #                     "webview_height_ratio": "tall",
    #                     "fallback_url": "https://petersfancybrownhats.com/"
    #                 },
    #                 "buttons":[{
    #                     "type":"postback",
    #                     "title":"Start Chatting",
    #                     "payload":"DEVELOPER_DEFINED_PAYLOAD"
    #                 }]
    #             },  {
    #                 "title": data[2]['stock_name']+"("+data[2]['stock_code']+")",
    #                 "image_url": "https://petersfancybrownhats.com/company_image.png",
    #                 "subtitle": data[2]['stock_busiType'],
    #                 "default_action":  {
    #                     "type": "web_url",
    #                     "url": "https://petersfancybrownhats.com/view?item=103",
    #                     "messenger_extensions": False,
    #                     "webview_height_ratio": "tall",
    #                     "fallback_url": "https://petersfancybrownhats.com/"
    #                 },
    #                 "buttons":[{
    #                     "type":"postback",
    #                     "title":"Start Chatting",
    #                     "payload":"DEVELOPER_DEFINED_PAYLOAD"
    #                 }]
    #             }]
    #         }
    #     }
    # })
    # print(type(generic_info))
    # send_generic(recipient_id, generic_info)


def send_message(recipient_id, message_text):
    print(type(message_text))

    log("sending message to {recipient}: {text}".format(recipient=recipient_id, text=message_text))

    params = {
        "access_token": os.environ["PAGE_ACCESS_TOKEN"]
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": message_text
        }
    })
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)


def send_generic(recipient_id, generic_info):

    log("sending message to {recipient}: {text}".format(recipient=recipient_id, text="generic"))

    params = {
        "access_token": os.environ["PAGE_ACCESS_TOKEN"]
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "recipient": {
            "id": recipient_id
        },
        "message": generic_info
    })
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)


def log(msg, *args, **kwargs):  # simple wrapper for logging to stdout on heroku
    try:
        if type(msg) is dict:
            msg = json.dumps(msg)
        else:
            msg = msg.format(*args, **kwargs)
        print(u"{}: {}".format(datetime.now(), msg))
    except UnicodeEncodeError:
        pass  # squash logging errors in case of non-ascii text
    sys.stdout.flush()


if __name__ == '__main__':
    app.run(debug=True)

