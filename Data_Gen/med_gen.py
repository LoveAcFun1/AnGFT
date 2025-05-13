import sys
import re
from tqdm import tqdm
import random
import json
import pandas as pd
import json
import time
import requests
import argparse
import copy
import os
import torch
from transformers import AutoTokenizer
from transformers import AutoModelForCausalLM

parser = argparse.ArgumentParser()
parser.add_argument('--document_path', type=str, required=True)
parser.add_argument('--out_put_path', type=str, required=True)
parser.add_argument('--area', type=str, required=True)

args = parser.parse_args()


def getAnswer_dev(query, user_name="", sender_name="", **params):
    """

    :param query:
    :param user_name: 必填，服务调用者的alias，
    :param sender_name: 选填，query发送者的名字，默认为空
    :param params: 一系列参数
    :return:
    """
    url = "" # the link of GPT

    value = {"request_id": f"{user_name}-{int(time.time() * 10000000)}",
             "bot_id": "1013",
             "business_id": "132",
             "user_name": user_name,
             "queries": [
                 {"msg_id": "340de8b6beee11ed9080525400dd089a",
                  "content": query,
                  "type": "text",
                  "name": sender_name}
             ],
             "context": []
             }
    value.update(params)
    value = json.dumps(value, ensure_ascii=False)

    postdata = {
        "task_id": "",
        "head": {
            "content_id": 1001092930389147672
        },
        "input": {
            "data": {
                "key": "data",
                "value": value,
                "type": "string"
            }
        }
    }

    r = requests.post(url, json=postdata)
    try:
        result = json.loads(r.text)
        return result
    except:
        return None


def parse_res(result) -> list:
    '''
    解析gpt结果
    '''
    chatgpt_reply = None
    if result and 'msg' in result and result['msg'] == 'succ':
        chatgpt_reply = json.loads(result['output']['data']['value'])['result']
        chatgpt_reply = [item['comment'] for item in chatgpt_reply]
    elif result.get("code") == 1:
        raise ValueError(f"{result['msg']}") 

    return chatgpt_reply


def retry_request_openai_summary(query, **params):
    result = []
    for i in range(3):
        result = getAnswer_dev(query, **params)
        try:
            result = parse_res(result)
        except:
            time.sleep(6)
            continue

        if not result:
            time.sleep(6)
            continue
        else:
            break

    return result

def retry_request_openai_no_parse(query, **params):
    result = []
    for i in range(3):
        result = getAnswer_dev(query, **params)
        
        if not result:
            time.sleep(6)
            continue
        else:
            break

    return result


path1 = args.document_path
Inputs = []
with open(path1, 'r') as f:
    lines = json.load(f)
    Inputs += lines

GPT_PROMPT = """
You need to give a more professional response based on the given {area} question:
    
    **Response steps**
    1. First, you need to identify the {area} entity in the question and explain its meaning.
    2. Secondly, if there are references related to the {area} entity, please list them.
    3. Thirdly, answer the questions in the question. Your answer should show your expertise in the {area} field as much as possible.
    4. Finally, you need to give corresponding {area} suggestions.
    
    **Requirements**
    Please strictly follow the steps to generate a response during the response process, but do not respond to the process name or the step name.
    Connect the answers with fluent sentences, and do not describe them in a stiff point-by-point manner.
    
    Please respond to the question based on the following references:
    **Reference**
    {response}
    
    **Question**
    {question}
    
    Output format:
    XXXX
"""

def gen_first_dia(id):
    prompt = GPT_PROMPT.format(area = args.area, question=Inputs[id]["input"], response = Inputs[id]["output"])
    res = retry_request_openai_summary(prompt)[0]
    res_lst = [item for item in res.split("\n") if item]
    return res_lst

def gen_GPT_first_chat(id):
    res_lst = gen_first_dia(id)
    return res_lst

OUT = []
for i in tqdm(range(len(Inputs))):
    res_lst = get_Qwen_res(i)
    out = '\n'.join(res_lst)
    op = copy.deepcopy(Inputs[i])
    op['output'] = out
    OUT.append(op)

file_name = args.out_put_path
f_out = open(file_name, 'w', encoding='utf-8')
f_out.write(json.dumps(OUT, ensure_ascii=False, indent=4))
f_out.close()