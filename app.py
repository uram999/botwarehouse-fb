# -*- coding: utf-8 -*-
import os
import sys
import json
import urllib.parse
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
                    elif "[" in message_text and "]" in message_text:
                        stock_modify_search(sender_id, message_text)
                    elif ">" in message_text:
                        stock_modify_search(sender_id, message_text)
                    elif "+" in message_text:
                        stock_add_search(sender_id, message_text)
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

                    if "INFO_PLAYLOAD" in postback or "BOT_START" in postback:
                        get_how_to_use(sender_id)

                    elif "LIST_PAYLOAD" in postback:
                        get_list_info(sender_id, user_id)

                    elif "POINT_PLAYLOAD" in postback:
                        get_estimate_info_all(sender_id, user_id)

                    elif "STOCK_MODIFY" in postback:
                        stock_modify_start(sender_id, payload_data)

                    elif "STOCK_UPDATE" in postback:
                        stock_modify_update(sender_id, user_id, payload_data)
                        get_list_info(sender_id, user_id)

                    elif "STOCK_REVERT" in postback:
                        stock_modify_revert(sender_id, user_id)

                    elif "STOCK_ADD" in postback:
                        stock_add_start(sender_id)

                    elif "STOCK_INSERT" in postback:
                        stock_add_update(sender_id, user_id, payload_data)
                        get_list_info(sender_id, user_id)

                    elif "STOCK_INDICATOR" in postback:
                        get_estimate_info(sender_id, user_id, payload_data)

                    elif "STOCK_NEWS" in postback:
                        get_stock_news(sender_id, payload_data)
                    pass

    return "ok", 200


# User_id 조회 Func : Facebook Messenger Id를 가지고 User_id 를 조회한다.
def get_user_id(recipient_id):
    api_url = os.environ["SERVER_URL"] + '/stock/get_user_id?fb_id={fb_id}'.format(fb_id=recipient_id)
    response = requests.get(api_url)

    data = json.loads(response.text)

    return data['naver_id']


# 설명 보기 Func : ChatBot 의 사용을 설명한다.
def get_how_to_use(recipient_id):
    send_message(recipient_id, "========= 사 용 방 법 ========= ")
    send_message(recipient_id, "1. 설명 보기 : 사용 방법을 볼 수 있다.")
    send_message(recipient_id, "2. 내 관심종목 : 등록된 내 관심종목을 보여줍니다")
    send_message(recipient_id, "3. 지표 보기 : 등록된 관심종목의 매수/매도 지표를 보여줍니다")


# 관심종목 보기 Func : 내가 등록한 관심종목을 보여준다.
def get_list_info(recipient_id, user_id):
    send_message(recipient_id, "등록되어 있는 관심 종목들을 알려드릴게요!")

    api_url = os.environ["SERVER_URL"] + '/stock/get_stock_list?user_id={user_id}'.format(user_id=user_id)
    response = requests.get(api_url)

    data = json.loads(response.text)
    generic_info = make_stock_list_generic(data)
    send_generic(recipient_id, generic_info)


# 전체종목 지표 보기 Func : 등록된 관심종목 전체의 지표를 보여준다.
def get_estimate_info_all(recipient_id, user_id):
    api_url = os.environ["SERVER_URL"] + '/stock/get_stock_estimate_all?user_id={user_id}'.format(user_id=user_id)
    response = requests.get(api_url)

    stock_estimate_info_list = json.loads(response.text)

    send_message(recipient_id, "관심 종목의 지표를 알려드릴게요!")
    for info in stock_estimate_info_list:
        send_message(recipient_id, "[{name}] 의 오늘 분석을 알려드릴게요!"
                     .format(name=info['stock']))

        send_message(recipient_id, "매수지표 : {ask}\n매도지표 : {bid}\n"
                     .format(ask=info['ask'], bid=info['bid']))

        if info['ask'] > 75:
            send_message(recipient_id, "으음... 조금더 질러 볼까요? 하하")

        if info['bid'] > 75:
            send_message(recipient_id, "팔때는 고민하시면 안됩니다! 어서 파세요!")
        send_message(recipient_id, "============================ ")


# 종목 지표 보기 Func : 지정한 종목의 지표를 보여준다.
def get_estimate_info(sender_id, user_id, payload_data):
    api_url = os.environ["SERVER_URL"] \
              + '/stock/get_stock_estimate?user_id={user_id}&code={code}'.format(user_id=user_id, code=payload_data[2])
    response = requests.get(api_url)

    stock_estimate_info = json.loads(response.text)[0]

    send_message(sender_id, "[{name}] 의 오늘 분석을 알려드릴게요!"
                 .format(name=stock_estimate_info['stock']))

    send_message(sender_id, "매수지표 : {ask}\n매도지표 : {bid}\n"
                 .format(ask=stock_estimate_info['ask'], bid=stock_estimate_info['bid']))

    if stock_estimate_info['ask'] > 75:
        send_message(sender_id, "으음... 조금더 질러 볼까요? 하하")

    if stock_estimate_info['bid'] > 75:
        send_message(sender_id, "팔때는 고민하시면 안됩니다! 어서 파세요!")
    send_message(sender_id, "============================ ")


# 종목 뉴스 보기 Func : 지정한 종목의 뉴스를 보여준다.
def get_stock_news(recipient_id, payload_data):
    send_message(recipient_id, "종목번호:{code} 의 베스트 뉴스입니다.".format(code=payload_data[2]))

    api_url = os.environ["SERVER_URL"] + '/stock/get_stock_news?code=' + payload_data[2]
    response = requests.get(api_url)

    data = json.loads(response.text)
    generic_info = make_stock_news_generic(data)
    send_generic(recipient_id, generic_info)


def stock_modify_start(recipient_id, payload_data):
    send_message(recipient_id, "종목번호:{code} 의 종목수정을 시작합니다.".format(code=payload_data[2]))
    send_message(recipient_id, "수정하고 싶은 종목코드와 새로운 종목코드를 입력 해 주세요.")
    send_message(recipient_id, "Ex) (수정전) > (수정후) \n094280 > 035420")


def stock_modify_search(recipient_id, text):
    pre_code = text.split(">")[0].strip()
    new_code = text.split(">")[1].strip()
    search_data = stock_search(new_code)

    if search_data['success']:
        send_message(recipient_id, "검색된 종목이 있습니다.")
        send_message(recipient_id, "검색된 종목이 맞는지 확인 해 주세요!")

        generic_info = make_modify_stock_generic(search_data, pre_code, new_code)
        send_generic(recipient_id, generic_info)
    else:
        send_message(recipient_id, "지원되지 않은 종목코드입니다.")
        send_message(recipient_id, "종목코드를 다시 한 번 확인 해 주세요!")


def stock_modify_revert(recipient_id, user_id):
    send_message(recipient_id, "종목 수정이 취소되었습니다!")
    get_estimate_info_all(recipient_id, user_id)
    reset_global()


def stock_modify_update(recipient_id, user_id, payload_data):
    url_param = {"user_id": user_id, "pre_code": payload_data[2], "new_code": payload_data[3]}
    api_url = os.environ["SERVER_URL"] + '/stock/update_stock_list?' + urllib.parse.urlencode(url_param)
    api_url = api_url.replace("amp;", "")
    response = requests.get(api_url)

    print(api_url)
    data = json.loads(response.text)

    send_message(recipient_id, "관심 종목이 수정되었습니다.")
    send_message(recipient_id, "{pre_name}({pre_code}) -> {new_name}({new_code})"\
        .format(pre_name=data['pre_stock']['stock_name'], pre_code=data['pre_stock']['stock_code'], new_name=data['new_stock']['stock_name'], new_code=data['new_stock']['stock_code']))


def stock_add_start(recipient_id):
    send_message(recipient_id, "신규 종목등록을 시작합니다.")
    send_message(recipient_id, "등록하고 싶은 종목코드를 입력 해 주세요.")
    send_message(recipient_id, "Ex) +(종목코드) \n+094280")


def stock_add_search(recipient_id, text):
    new_code = text.split("+")[1].strip()
    search_data = stock_search(new_code)

    if search_data['success']:
        send_message(recipient_id, "검색된 종목이 있습니다.")
        send_message(recipient_id, "검색된 종목이 맞는지 확인 해 주세요!")

        generic_info = make_add_stock_generic(search_data, new_code)
        send_generic(recipient_id, generic_info)
    else:
        send_message(recipient_id, "지원되지 않은 종목코드입니다.")
        send_message(recipient_id, "종목코드를 다시 한 번 확인 해 주세요!")


def stock_add_update(recipient_id, user_id, payload_data):
    api_url = os.environ["SERVER_URL"] \
        + '/stock/add_stock_list?user_id={user_id}&code={new_code}'\
        .format(user_id=user_id, new_code=payload_data[2])
    response = requests.get(api_url)

    data = json.loads(response.text)[0]

    send_message(recipient_id, "관심 종목이 등록되었습니다.")
    send_message(recipient_id, "{new_name}({new_code})"\
        .format(new_name=data['stock_name'], new_code=data['stock_code']))


def stock_search(code):
    api_url = os.environ["SERVER_URL"] + '/stock/search_stock_list?code={code}'.format(code=code)
    response = requests.get(api_url)

    data = json.loads(response.text)[0]

    return data


# 뉴스 Generic Maker Func
def make_stock_news_generic(news_lists):
    result_json = []

    for news in news_lists:

        action_json = {
            "type": 'web_url',
            "url": news['link'],
            "messenger_extensions": False,
            "webview_height_ratio": 'COMPACT'
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


# 전체종목 Generic Maker Func
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
        if "미등록" in stock['stock_name']:
            button_data = {
                "type": 'postback',
                "title": '종목 등록',
                "payload": 'STOCK_ADD'
            }
            button_json.append(button_data)

        else:
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
            "image_url": os.environ["NOSTOCK_IMAGE"] if "미등록" in stock['stock_name'] else os.environ["MAIN_IMAGE"],
            "default_action": action_json,
            "buttons": button_json,
        }
        result_json.append(result_data)

    temp = json.dumps(result_json)
    return json.loads(temp)


# 수정종목 Generic Maker Func
def make_modify_stock_generic(stock, pre_code, new_code):

    result_json = []

    action_json = {
        "type": 'web_url',
        "url": 'https://finance.naver.com/item/main.nhn?code=' + stock['stock_code'],
        "messenger_extensions": False,
        "webview_height_ratio": 'tall'
    }

    button_json = []
    button_data = {
        "type": 'postback',
        "title": '수정 하기',
        "payload": 'STOCK_UPDATE_{pre_code}_{new_code}'.format(pre_code=pre_code, new_code=new_code)
    }
    button_json.append(button_data)

    button_data = {
        "type": 'postback',
        "title": '수정 취소',
        "payload": 'STOCK_REVERT'
    }
    button_json.append(button_data)

    result_data = {
        "title": stock['stock_name'] + "(" + stock['stock_code'] + ")",
        "subtitle": stock['stock_type'],
        "image_url": os.environ["MAIN_IMAGE"],
        "default_action": action_json,
        "buttons": button_json,
    }
    result_json.append(result_data)

    temp = json.dumps(result_json)
    return json.loads(temp)


# 추가종목 Generic Maker Func
def make_add_stock_generic(stock, new_code):

    result_json = []

    action_json = {
        "type": 'web_url',
        "url": 'https://finance.naver.com/item/main.nhn?code=' + stock['stock_code'],
        "messenger_extensions": False,
        "webview_height_ratio": 'tall'
    }

    button_json = []
    button_data = {
        "type": 'postback',
        "title": '등록 하기',
        "payload": 'STOCK_INSERT_{new_code}'.format(new_code=new_code)
    }
    button_json.append(button_data)

    result_data = {
        "title": stock['stock_name'] + "(" + stock['stock_code'] + ")",
        "subtitle": stock['stock_type'],
        "image_url": os.environ["MAIN_IMAGE"],
        "default_action": action_json,
        "buttons": button_json,
    }
    result_json.append(result_data)

    temp = json.dumps(result_json)
    return json.loads(temp)


# FB Text Message Send API
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


# FB Generic Send API
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

