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

                sender_id = messaging_event["sender"]["id"]
                recipient_id = messaging_event["recipient"]["id"]  # the recipient's ID, which should be your page's facebook ID

                user_id = get_user_id(sender_id)

                if messaging_event.get("message"):  # someone sent us a message
                    message_text = messaging_event["message"]["text"]  # the message's text

                    if message_text == "보기":
                        get_list_info(sender_id)
                    else:
                        send_message(sender_id, "roger that!")

                if messaging_event.get("delivery"):  # delivery confirmation
                    pass

                if messaging_event.get("optin"):  # optin confirmation
                    pass

                if messaging_event.get("postback"):  # user clicked/tapped "postback" button in earlier message
                    postback = messaging_event["postback"]["payload"]
                    payload_data = postback.split("_")
                    print(postback)
                    print(payload_data)

                    if postback == "INFO_PLAYLOAD" or postback == "BOT_START":
                        get_how_to_use(sender_id)

                    elif postback == "LIST_PAYLOAD":
                        get_list_info(sender_id, user_id)

                    elif postback == "POINT_PLAYLOAD":
                        stock_estimate_info = get_estimate_info(user_id)
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

                    elif "STOCK_MODIFY" in postback:
                        pass

                    elif "STOCK_INDICATOR" in postback:
                        pass

                    elif "STOCK_NEWS" in postback:
                        get_stock_news(sender_id, user_id, payload_data)
                    pass

    return "ok", 200


def get_user_id(recipient_id):
    api_url = os.environ["SERVER_URL"] + '/stock/get_user_id?fb_id='+recipient_id
    response = requests.get(api_url)

    data = json.loads(response.text)

    return data['naver_id']


def get_how_to_use(recipient_id):
    send_message(recipient_id, "========= 사 용 방 법 ========= ")
    send_message(recipient_id, "1. 설명 보기 : 사용 방법을 볼 수 있다.")
    send_message(recipient_id, "2. 내 관심종목 : 등록된 내 관심종목을 보여줍니다")
    send_message(recipient_id, "3. 지표 보기 : 등록된 관심종목의 매수/매도 지표를 보여줍니다")


def get_list_info(recipient_id, user_id):
    send_message(recipient_id, "등록되어 있는 관심 종목들을 알려드릴게요!")

    api_url = os.environ["SERVER_URL"] + '/stock/get_stock_list?user_id='+user_id
    response = requests.get(api_url)

    data = json.loads(response.text)
    generic_info = make_stock_list_generic(data)
    send_generic(recipient_id, generic_info)


def get_estimate_info(user_id):
    api_url = os.environ["SERVER_URL"] + '/stock/get_stock_estimate?user_id=' + user_id
    response = requests.get(api_url)

    data = json.loads(response.text)
    print(data)
    return data


def get_stock_news(recipient_id, user_id, payload_data):
    send_message(recipient_id, "종목번호:{code} 의 베스트 뉴스입니다.".format(code=payload_data[2]))

    api_url = os.environ["SERVER_URL"] + '/stock/get_stock_news?code=' + payload_data[2]
    response = requests.get(api_url)

    data = json.loads(response.text)
    generic_info = make_stock_news_generic(data)
    send_generic(recipient_id, generic_info)


def make_stock_news_generic(news_lists):
    result_json = []

    for news in news_lists:

        action_json = {
            "type": 'web_url',
            "url": news['link'],
            "messenger_extensions": False,
            "webview_height_ratio": 'tall'
        }

        button_json = []
        button_data = {
            "type": 'web_url',
            "title": '상세 보기',
            "url": news['link']
        }
        button_json.append(button_data)

        result_data = {
            "title": news['title'],
            "subtitle": '',
            "image_url": os.environ["NEWS_IMAGE"],
            "default_action": action_json,
            "buttons": button_json,
        }
        result_json.append(result_data)

    temp = json.dumps(result_json)
    return json.loads(temp)


def make_stock_list_generic(stock_lists):
    result_json = []

    for stock in stock_lists:

        action_json = {
            "type": 'web_url',
            "url": 'https://finance.naver.com/item/main.nhn?code='+stock['stock_code'],
            "messenger_extensions": False,
            "webview_height_ratio": 'tall'
        }

        button_json = []
        button_data = {
            "type": 'postback',
            "title": '종목 수정',
            "payload": 'STOCK_MODIFY_'+stock['stock_code']
        }
        button_json.append(button_data)

        button_data = {
            "type": 'postback',
            "title": '지표 보기',
            "payload": 'STOCK_INDICATOR_'+stock['stock_code']
        }
        button_json.append(button_data)

        button_data = {
            "type": 'postback',
            "title": '추천 뉴스',
            "payload": 'STOCK_NEWS_'+stock['stock_code']
        }
        button_json.append(button_data)

        result_data = {
            "title": stock['stock_name']+"("+stock['stock_code']+")",
            "subtitle": stock['stock_busiType'],
            "image_url": os.environ["MAIN_IMAGE"],
            "default_action": action_json,
            "buttons": button_json,
        }
        result_json.append(result_data)

    temp = json.dumps(result_json)
    return json.loads(temp)


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

    print(data)

    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)

    if r.status_code != 200:
        # log(r.status_code)
        # log(r.text)
        print(r.status_code)
        print(r.text)


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

