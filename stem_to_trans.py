import os
import re
import json

files = os.listdir('./corpus/conlab_bashkir/')

for f in files:
    print(f)
    with open('./corpus/conlab_bashkir/' + f, 'r', encoding='utf-8') as fil:
        text = json.loads(fil.read())
    for sent in text['sentences']:
        for word in sent['words']:
            if 'ana' in word:
                if word['ana']:
                    anat = word['ana'][0]
                    if 'gloss_index' in anat:
                        if '{' in anat['gloss_index']:
                            eng = re.search('(.*?){', anat['gloss_index']).group(1)
                        else:
                            eng = anat['gloss_index']
                        anat['gloss_index'] = anat['gloss_index'].replace(eng, 'STEM')
                        #anat['gloss'] = anat['gloss'].replace(eng, 'STEM')
                        anat['trans_en'] = eng
    with open('./corpus/conlab_bashkir/' + f, 'w', encoding='utf-8') as fw:
        json.dump(text, fw, ensure_ascii=False)
