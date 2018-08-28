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

                    if message_text == "보기":
                        get_list_info_gen(sender_id)
                    else:
                        send_message(sender_id, "roger that!")

                if messaging_event.get("delivery"):  # delivery confirmation
                    pass

                if messaging_event.get("optin"):  # optin confirmation
                    pass

                if messaging_event.get("postback"):  # user clicked/tapped "postback" button in earlier message
                    sender_id = messaging_event["sender"]["id"]
                    postback = messaging_event["postback"]["payload"]

                    if postback == "INFO_PLAYLOAD" or postback == "BOT_START":
                        send_message(sender_id, "========= 사 용 방 법 ========= ")
                        send_message(sender_id, "1. 설명 보기 : 사용 방법을 볼 수 있다.")
                        send_message(sender_id, "2. 내 관심종목 : 등록된 내 관심종목을 보여줍니다")
                        send_message(sender_id, "3. 지표 보기 : 등록된 관심종목의 매수/매도 지표를 보여줍니다")

                    elif postback == "LIST_PAYLOAD":
                        stock_list_info = get_list_info()
                        send_message(sender_id, "등록되어 있는 관심 종목들을 알려드릴게요!")
                        for info in stock_list_info:
                            send_message(sender_id, "{name} ({code}) - {busiType}"
                                         .format(name=info['stock_name'], code=info['stock_code'], busiType=info['stock_busiType']))

                    elif postback == "POINT_PLAYLOAD":
                        stock_estimate_info = get_estimate_info()
                        send_message(sender_id, "관심 종목의 지표를 알려드릴게요!")
                        for info in stock_estimate_info:
                            send_message(sender_id, "[{name}] 의 오늘 분석을 알려드릴게요!"
                                         .format(name=info['stock']))

                            send_message(sender_id, "매수지표 : {ask}\n매도지표 : {bid}\n"
                                         .format(ask=info['ask'], bid=info['bid']))

                            if info['ask'] > 75:
                                send_message(sender_id, "으음... 조금더 질러 볼까요? 하하")

                            if info['bid'] > 75:
                                send_message(sender_id, "팔때는 고민하시면 안됩니다! 어서 파세요!")
                            send_message(sender_id, "============================ ")
                    pass

    return "ok", 200


def get_list_info_gen(recipient_id):
    URL = os.environ["SERVER_URL"] + '/stock/get_stock_list?user_id=uram999'
    response = requests.get(URL)

    data = json.loads(response.text)
    generic_info = make_generic(data)

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
    send_generic(recipient_id, generic_info)


def make_generic(stock_lists):
    result_json = []

    for stock in stock_lists:
        action_json = []
        button_json = []

        action_data = {
            'type': 'web_url',
            'url': 'https://www.facebook.com/BotWarehouse-1498183390311752/?modal=admin_todo_tour',
            'messenger_extensions': False,
            'webview_height_ratio': 'tall',
            'fallback_url': 'https://petersfancybrownhats.com/'
        }
        action_json.append(action_data)

        button_data = {
            'type': 'postback',
            'title': '종목수정',
            'playload': 'STOCK_MODIFY'
        }
        button_json.append(button_data)

        result_data = {
            'title': stock['stock_name']+"("+stock['stock_code']+")",
            'subtitle': stock['stock_busiType'],
            'image_url': 'https://scontent-icn1-1.xx.fbcdn.net/v/t1.0-9/38511998_1498186563644768_5962859944947482624_o.jpg?_nc_cat=0&oh=778b88d1ef3fc7bef74a8f7db5cef3b8&oe=5BEE2966',
            'default_action': action_json,
            'buttons': button_json,
        }
        result_json.append(result_data)

    temp = json.dumps(result_json)
    print(json.loads(temp))


def get_list_info():
    URL = os.environ["SERVER_URL"] + '/stock/get_stock_list?user_id=uram999'
    response = requests.get(URL)

    data = json.loads(response.text)
    return data


def get_estimate_info():
    URL = os.environ["SERVER_URL"] + '/stock/get_stock_estimate?user_id=uram999'
    response = requests.get(URL)

    data = json.loads(response.text)
    print(data)
    return data


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
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "generic",
                    "elements": generic_info
                }
            }
        }
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

