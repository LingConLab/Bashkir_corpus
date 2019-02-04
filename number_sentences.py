import os
import re
import json

files = os.listdir('./corpus/conlab_bashkir/')


for f in files:
    print(f)
    i = 1
    with open('./corpus/conlab_bashkir/' + f, 'r', encoding='utf-8') as fil:
        text = json.loads(fil.read())
    for sent in text['sentences']:
         if sent['lang'] == 0:
                if len(str(i)) == 1:
                    number = '00' + str(i)
                elif len(str(i)) == 2:
                    number = '0' + str(i)
                else:
                    number = str(i)
                sent['number'] = number
                i += 1
                step = i
         else:
                if len(str(i-step+1)) == 1:
                    number = '00' + str(i-step+1)
                elif len(str(i-step+1)) == 2:
                    number = '0' + str(i-step+1)
                else:
                    number = str(i-step+1)
                sent['number'] = number
                i += 1
    with open('./corpus/conlab_bashkir/' + f, 'w', encoding='utf-8') as fw:
        json.dump(text, fw, ensure_ascii=False,
                  indent=1)
