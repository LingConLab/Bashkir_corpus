from lxml import etree
import os
import re
import copy


with open('not_regular_bashkir_lemmas.csv', 'r') as f:
    lines = f.readlines()
    not_regular_lemmas = {line.split(',')[0]: [line.split(',')[1], line.split(',')[2]] for line in lines}


lemmas = dict()
def get_lemma(stem, pos, ruGloss=''):
    
    lemma = ''
    rustem = re.findall('[а-яё]+', ruGloss)
    
    if stem in not_regular_lemmas:
        lemma = not_regular_lemmas[stem][1]        
        
    elif stem == 'bar' and rustem[0] == 'идти':
        lemma = 'barəw'
    elif stem == 'bar' and rustem[0] == 'имеется':
        lemma = 'bar'
    elif stem == 'tej' and rustem[0] == 'говорить':
        lemma = 'tiew'
    elif stem == 'tej' and rustem[0] == 'касаться':
        lemma = 'tejew'
        
    else:
        if pos == 'v':
            lemma = stem
            if stem.endswith('p'):
                lemma = re.sub('p$', 'b', stem)
            elif stem.endswith('k'):
                lemma = re.sub('k$', 'g', stem)
            elif stem.endswith('q'):
                lemma = re.sub('q$', 'ɣ', stem)
            
            if re.search('[^əauoeäüiö]$', stem):
                last_vowel = re.findall('[əauoeäüiö]', stem)[-1]
                if last_vowel == 'ə' or last_vowel == 'a' or last_vowel == 'u':
                    lemma += 'ə'
                elif last_vowel == 'o':
                    lemma += 'o'
                elif last_vowel == 'e' or last_vowel == 'ä' or last_vowel == 'ü' or last_vowel == 'i':
                    lemma += 'e'
                elif last_vowel == 'ö':
                    lemma += 'ö'
            lemma += 'w'

        elif pos == 'n' or pos == 'num' or pos == 'adj' or pos == 'post' or pos == 'intens~adj':
            if stem.endswith('b'):
                lemma = re.sub('b$', 'p', stem)
            elif stem.endswith('g'):
                lemma = re.sub('g$', 'k', stem)
            elif stem.endswith('ɣ'):
                lemma = re.sub('ɣ$', 'q', stem)
            else:
                lemma = stem
            
    return lemma
    
    
class ConLabEAFConvertor:
    """
    Contains methods for converting eafs in the old ConLab
    to the new ConLab format and adding grammatical tags
    in the process.
    """
    rxSplitParts = re.compile('(?:^|[-=.])[^-=а-яёА-ЯЁ ]+|<[^<>]+>')
    rxWord = re.compile('\\b\\w[\\w-]*\\w\\b|\\b\\w\\b')

    def __init__(self):
        self.srcDir = 'eaf_to_process'
        self.targetDir = 'eaf'
        self.tlis = {}      # time labels
        self.rxTierType = re.compile('^(id|tx|mb|ge|gr|ft|ps)@(.+)$')
        self.lastUsedAID = 0
        self.refTiers = {}
        self.sentences = {}
        self.wordTiers = {}
        self.idTiers = {}
        self.morphTiers = {}
        self.lemmaTiers = {}
        self.posTiers = {}
        self.glossEnTiers = {}
        self.glossRuTiers = {}
        self.removedSegmentIDs = set()
        self.aid2pos = {}
        self.aid2ruGloss = {}
        self.grammRules = []
        self.load_gramm_rules('gramRules.txt')

    @staticmethod
    def prepare_rule(rule):
        """
        Make a compiled regex out of a rule represented as a string.
        """
        def replReg(s):
            if "'" in s:
                return ''
            return ' re.search(\'' + s +\
                   '\', parts) is not None or ' +\
                   're.search(\'' + s +\
                   '\', gloss) is not None '
        ruleParts = rule.split('"')
        rule = ''
        for i in range(len(ruleParts)):
            if i % 2 == 0:
                rule += re.sub('([^\\[\\]~|& \t\']+)', ' \'\\1\' in tagsAndGlosses ',
                               ruleParts[i]).replace('|', ' or ').replace('&', ' and ')\
                                            .replace('~', ' not ').replace('[', '(').replace(']', ')')
            else:
                rule += replReg(ruleParts[i])
        return rule

    def load_gramm_rules(self, fname):
        """
        Load main set of rules for converting the glosses into bags
        of grammatical tags.
        """
        if len(fname) <= 0 or not os.path.isfile(fname):
            return
        rules = []
        f = open(fname, 'r', encoding='utf-8-sig')
        for line in f:
            line = line.strip()
            if len(line) > 0:
                rule = [i.strip() for i in line.split('->')]
                if len(rule) != 2:
                    continue
                rule[1] = set(rule[1].split(','))
                rule[0] = self.prepare_rule(rule[0])
                rules.append(rule)
        f.close()
        self.grammRules = rules

    def restore_gramm(self, pos, gloss, parts=''):
        """
        Restore grammatical tags from the glosses using the rules
        provided in gramRules.txt.
        """
        if ' .' in gloss:
            print(gloss)
        grammTags = set()
        tagsAndGlosses = set()
        if len(pos) > 0:
            tagsAndGlosses.add(pos)
        tagsAndGlosses |= set(gl.strip('-=:.~<>')
                              for gl in self.rxSplitParts.findall(gloss))
        if len(self.grammRules) > 0:
            for rule in self.grammRules:
                if eval(rule[0]):
                    grammTags |= rule[1]
        for gl in tagsAndGlosses:
            if gl == pos:
                continue
            gl = gl.lower()
            if gl == "ipfv.1sg":
                grammTags.add(gl.split('.')[0])
                grammTags.add(gl.split('.')[1])
            else:
                grammTags.add(gl)
        return ','.join(sorted(grammTags))

    def get_tlis(self, srcTree):
        """
        Retrieve and return all time labels from the XML tree.
        """
        tlis = {}
        iTli = 0
        for tli in srcTree.xpath('/ANNOTATION_DOCUMENT/TIME_ORDER/TIME_SLOT'):
            timeValue = ''
            if 'TIME_VALUE' in tli.attrib:
                timeValue = tli.attrib['TIME_VALUE']
            tlis[tli.attrib['TIME_SLOT_ID']] = {'n': iTli, 'time': timeValue}
            iTli += 1
        return tlis

    def traverse_tree(self, srcTree, callback):
        for tierNode in srcTree.xpath('/ANNOTATION_DOCUMENT/TIER'):
            if 'TIER_ID' not in tierNode.attrib:
                continue
            tierID = tierNode.attrib['TIER_ID']
            mTierType = self.rxTierType.search(tierID)
            if mTierType is None:
                continue
            participant = mTierType.group(2)
            tierType = mTierType.group(1)
            callback(tierNode, tierType, participant)

    def get_tier_segment_ids(self, tierNode):
        """
        For an association-aligned tier, return a dictionary
        {ID of the parent annotation -> ID of the current annotation}
        """
        segIDs = {}
        for node in tierNode.xpath('ANNOTATION/REF_ANNOTATION'):
            segIDs[node.attrib['ANNOTATION_REF']] = node.attrib['ANNOTATION_ID']
        return segIDs

    def get_segment_values(self, tierNode):
        """
        Return a dictionary {annotation ID -> annotation text}
        """
        segIDs = {}
        for node in tierNode.xpath('ANNOTATION/REF_ANNOTATION'):
            segIDs[node.attrib['ANNOTATION_ID']] = node.xpath('ANNOTATION_VALUE')[0].text
        return segIDs

    def get_annotation_ids_one_tier(self, tierNode, tierType, participant):
        if tierType not in ('id', 'tx', 'mb', 'ge', 'gr', 'ps'):
            return
        segIDs = self.get_tier_segment_ids(tierNode)
        #print(segIDs)
        if tierType == 'tx':
            self.wordTiers[participant] = segIDs
            for segment in tierNode.xpath('ANNOTATION/REF_ANNOTATION'):
                if 'PREVIOUS_ANNOTATION' in segment.attrib:
                    self.sentences[segment.attrib['ANNOTATION_REF']] += ' ' + segment.xpath('ANNOTATION_VALUE')[0].text
                else:
                    self.sentences[segment.attrib['ANNOTATION_REF']] = segment.xpath('ANNOTATION_VALUE')[0].text
        elif tierType == 'ps':
            self.posTiers[participant] = segIDs
            self.aid2pos.update(self.get_segment_values(tierNode))
        elif tierType == 'mb':
            self.morphTiers[participant] = segIDs
        elif tierType == 'ge':
            self.glossEnTiers[participant] = segIDs
        elif tierType == 'id':
            self.idTiers[participant] = segIDs
        elif tierType == 'gr':
            self.glossRuTiers[participant] = segIDs
            self.aid2ruGloss.update(self.get_segment_values(tierNode))

    def get_annotation_ids(self, srcTree):
        """
        Traverse the tree and save data from the Lemma, POS,
        Morph and Gloss tiers for later use.
        """
        self.aid2pos = {}
        self.traverse_tree(srcTree, self.get_annotation_ids_one_tier)

    def read_ref_tier(self, tierNode):
        """
        Read the time-aligned baseline (reference) tier and
        save its data for later use.
        """
        aID2sent = {}
        segments = tierNode.xpath('ANNOTATION/ALIGNABLE_ANNOTATION')
        for segment in segments:
            if 'ANNOTATION_ID' in segment.attrib:
                aID = segment.attrib['ANNOTATION_ID']
                try:
                    aID2sent[aID] = segment.xpath('ANNOTATION_VALUE')[0].text.strip()
                except AttributeError:
                    aID2sent[aID] = ''
            else:
                continue
        return aID2sent

    def get_word_tier(self, morphTierNode, participant):
        """
        Make and return a Word tier out of Morph tier
        """
        wordTierNode = copy.deepcopy(morphTierNode)
        wordTierNode.attrib['TIER_ID'] = wordTierNode.attrib['TIER_ID'].replace('_Morph', '_Word')
        sent2words = {}
        for sentID in self.refTiers[participant]:
            sent2words[sentID] = self.rxWord.findall(self.refTiers[participant][sentID].lower())
        iWord = 0
        prevSentID = ''
        for segment in wordTierNode.xpath('ANNOTATION/REF_ANNOTATION'):
            curSentID = segment.attrib['ANNOTATION_REF']
            if curSentID != prevSentID:
                iWord = 0
            prevSentID = curSentID
            wordFromMorph = re.sub('[-0]', '', segment.xpath('ANNOTATION_VALUE')[0].text)
            if iWord < len(sent2words[curSentID]):
                if (sent2words[curSentID][iWord] != wordFromMorph
                        and iWord < len(sent2words[curSentID]) - 1
                        and sent2words[curSentID][iWord + 1] == wordFromMorph):
                    iWord += 1      # simple fix for single incomplete tokens
                segment.xpath('ANNOTATION_VALUE')[0].text = sent2words[curSentID][iWord]
            else:
                segment.xpath('ANNOTATION_VALUE')[0].text = wordFromMorph
            iWord += 1
        return wordTierNode

    def get_sentence_tier(self, refTierNode, participant):
        """
        Make and return a Word tier out of Morph tier
        """
        sentenceTierNode = copy.deepcopy(refTierNode)
        sentenceTierNode.attrib['TIER_ID'] = sentenceTierNode.attrib['TIER_ID'].replace('_Ref', '_Transcription')
        for segment in sentenceTierNode.xpath('ANNOTATION/REF_ANNOTATION | ANNOTATION/ALIGNABLE_ANNOTATION'):
            sentenceText = self.sentences[segment.attrib['ANNOTATION_ID']]
            if re.search('[.?!:;,/] *$', sentenceText) is None:
                sentenceText += '.'
            segment.xpath('ANNOTATION_VALUE')[0].text = sentenceText
        return sentenceTierNode	    

    def get_lemma_tier(self, morphTierNode, participant):
        """
        Make and return a Gramm tier out of a Morph tier (using
        previously saved POS data)
        """
        lemmaTierNode = copy.deepcopy(morphTierNode)
        lemmaTierNode.attrib['TIER_ID'] = lemmaTierNode.attrib['TIER_ID'].replace('_Morph', '_Lemma')
        lemmaTierNode.attrib['PARENT_REF'] = lemmaTierNode.attrib['PARENT_REF'].replace('_POS', '_Word')
        for segment in lemmaTierNode.xpath('ANNOTATION/REF_ANNOTATION'):
            curPosID = segment.attrib['ANNOTATION_ID']
            pos = self.aid2pos[self.posTiers[participant][curPosID]]
            stem = re.sub('(?<=.)[-=].*', '', segment.xpath('ANNOTATION_VALUE')[0].text).strip('-=')
            try:
                ruGloss = self.aid2ruGloss[self.glossRuTiers[participant][curPosID]]
                lemma = get_lemma(stem, pos, ruGloss)
            except:
                lemma = get_lemma(stem, pos)
            segment.xpath('ANNOTATION_VALUE')[0].text = lemma

        return lemmaTierNode

    def get_gramm_tier(self, morphTierNode):
        """
        Make and return a Gramm tier out of a Morph tier (using
        previously saved POS data)
        """
        grammTierNode = copy.deepcopy(morphTierNode)
        grammTierNode.attrib['TIER_ID'] = grammTierNode.attrib['TIER_ID'].replace('_Gloss', '_Gramm')
        for segment in grammTierNode.xpath('ANNOTATION/REF_ANNOTATION'):
            curPosID = segment.attrib['ANNOTATION_REF']
            pos = self.aid2pos[curPosID]
            gloss = segment.xpath('ANNOTATION_VALUE')[0].text.replace(' .', '-')
            segment.xpath('ANNOTATION_VALUE')[0].text = self.restore_gramm(pos, gloss)
        return grammTierNode

    def reindex_segments(self, tierNode):
        """
        Assign all tier annotations new IDs.
        """
        for segment in tierNode.xpath('ANNOTATION/REF_ANNOTATION | ANNOTATION/ALIGNABLE_ANNOTATION'):
            if 'PREVIOUS_ANNOTATION' in segment.attrib:
                segment.attrib['PREVIOUS_ANNOTATION'] = 'a' + str(self.lastUsedAID)
            self.lastUsedAID += 1
            segment.attrib['ANNOTATION_ID'] = 'a' + str(self.lastUsedAID)

    def reattach_morph_segments(self, tierNode, segmentIDs, participant):
        """
        Attach the Morph tier annotations to POS, instead of Transcription.
        """
        for segment in tierNode.xpath('ANNOTATION/REF_ANNOTATION'):
            if 'PREVIOUS_ANNOTATION' in segment.attrib:
                del segment.attrib['PREVIOUS_ANNOTATION']
            try:
                segment.attrib['ANNOTATION_REF'] = segmentIDs[participant][segment.attrib['ANNOTATION_ID']]
            except KeyError:
                segment.getparent().getparent().remove(segment.getparent())

    def reattach_non_morph_segments(self, tierNode, segmentIDs, participant):
        """
        Attach any association-aligned tier to another tier.
        """
        for segment in tierNode.xpath('ANNOTATION/REF_ANNOTATION'):
            if 'PREVIOUS_ANNOTATION' in segment.attrib:
                del segment.attrib['PREVIOUS_ANNOTATION']
            try:
                segment.attrib['ANNOTATION_REF'] = segmentIDs[participant][segment.attrib['ANNOTATION_REF']]
            except KeyError:
                segment.getparent().getparent().remove(segment.getparent())

    def collapse_glosses_in_tier(self, tierNode, tierType, participant):
        if tierType not in ('mb', 'ge', 'gr', 'ps'):
            return
        prevNode = None
        for segment in tierNode.xpath('ANNOTATION/REF_ANNOTATION'):
            if ('PREVIOUS_ANNOTATION' not in segment.attrib
                    and segment.attrib['ANNOTATION_REF'] not in self.removedSegmentIDs):
                segment.xpath('ANNOTATION_VALUE')[0].text = re.sub('(?<=.)[-=](?=.)', '.',
                                                                   segment.xpath('ANNOTATION_VALUE')[0].text)
                prevNode = segment
            else:
                if tierType != 'ps':
                    prevNode.xpath('ANNOTATION_VALUE')[0].text += re.sub('(?<=.)[-=](?=.)', '.',
                                                                         segment.xpath('ANNOTATION_VALUE')[0].text)
                elif '-' not in segment.xpath('ANNOTATION_VALUE')[0].text:
                    prevNode.xpath('ANNOTATION_VALUE')[0].text = re.sub('(?<=.)[-=](?=.)', '.',
                                                                        segment.xpath('ANNOTATION_VALUE')[0].text)
                self.removedSegmentIDs.add(segment.attrib['ANNOTATION_ID'])
                segment.getparent().getparent().remove(segment.getparent())

    def collapse_glosses(self, srcTree):
        """
        Attach any association-aligned tier to another tier.
        """
        self.traverse_tree(srcTree, self.collapse_glosses_in_tier)

    def convert_one_tier(self, tierNode, tierType, participant):
        parentNode = tierNode.getparent()
        tierIndex = parentNode.index(tierNode)
        if tierType == 'id':
            tierNode.attrib['TIER_ID'] = participant + '_Ref-txt-bak'
            sentenceTier = self.get_sentence_tier(tierNode, participant)
            parentNode.insert(tierIndex + 1, sentenceTier)
            self.reindex_segments(tierNode)
            newRefIds = []
            for segment in tierNode.xpath('ANNOTATION/REF_ANNOTATION | ANNOTATION/ALIGNABLE_ANNOTATION'):
                newRefIds.append(segment.attrib['ANNOTATION_ID'])
            sentenceSegments = sentenceTier.xpath('ANNOTATION/ALIGNABLE_ANNOTATION')
            for i in range(len(newRefIds)):
                sentenceSegments[i].tag = 'REF_ANNOTATION'
                del sentenceSegments[i].attrib['TIME_SLOT_REF1']
                del sentenceSegments[i].attrib['TIME_SLOT_REF2']
                sentenceSegments[i].attrib['ANNOTATION_REF'] = newRefIds[i]
            sentenceTier.attrib['LINGUISTIC_TYPE_REF'] = 'ft'
            sentenceTier.attrib['PARENT_REF'] = tierNode.attrib['TIER_ID']
        if tierType in ('ft', 'src', 'com', 'tx'):
            tierNode.attrib['PARENT_REF'] = self.rxTierType.sub('\\2_Transcription-txt-bak',
                                                                tierNode.attrib['PARENT_REF'])
        if tierType == 'tx':
            for segment in tierNode.xpath('ANNOTATION/REF_ANNOTATION'):
                segment.xpath('ANNOTATION_VALUE')[0].text = segment.xpath('ANNOTATION_VALUE')[0].text.strip('.,()<>[]"\'\\/:;?!=')
            tierNode.attrib['TIER_ID'] = participant + '_Word-txt-bak'
        if tierType == 'mb':
            tierNode.attrib['TIER_ID'] = participant + '_Morph-txt-bak'
            tierNode.attrib['PARENT_REF'] = self.rxTierType.sub('\\2_POS-txt-bak',
                                                                tierNode.attrib['PARENT_REF'])
            parentNode.insert(tierIndex + 1, self.get_lemma_tier(tierNode, participant))
            self.reattach_morph_segments(tierNode, self.posTiers, participant)
            self.reindex_segments(tierNode)
        if tierType in ('ge', 'gr'):
            tierNode.attrib['PARENT_REF'] = self.rxTierType.sub('\\2_POS-txt-bak',
                                                                tierNode.attrib['PARENT_REF'])
        if tierType == 'ps':
            tierNode.attrib['PARENT_REF'] = self.rxTierType.sub('\\2_Lemma-txt-bak',
                                                                tierNode.attrib['PARENT_REF'])
            tierNode.attrib['TIER_ID'] = participant + '_POS-txt-bak'
        if tierType == 'ge':
            tierNode.attrib['TIER_ID'] = participant + '_Gloss-txt-en'
            self.reattach_non_morph_segments(tierNode, self.posTiers, participant)
        if tierType == 'gr':
            tierNode.attrib['TIER_ID'] = participant + '_Gloss-txt-ru'
            self.reattach_non_morph_segments(tierNode, self.posTiers, participant)
            parentNode.insert(tierIndex + 1, self.get_gramm_tier(tierNode))
            self.reindex_segments(tierNode)

    def convert_file(self, fnameSrc, fnameTarget):
        """
        Convert one EAF file and save the output as fnameTarget
        """
        srcTree = etree.parse(fnameSrc)
        self.tlis = self.get_tlis(srcTree)
        self.refTiers = {}      # participant -> {ID -> text}
        self.lastUsedAID = 0
        self.morphTiers = {}
        self.lemmaTiers = {}
        self.posTiers = {}
        self.glossTiers = {}
        self.removedSegmentIDs = set()
        self.aid2pos = {}
        self.lastUsedAID = int(srcTree.xpath('/ANNOTATION_DOCUMENT/HEADER/'
                                             'PROPERTY[@NAME=\'lastUsedAnnotationId\']')[0].text)
        self.collapse_glosses(srcTree)
        self.get_annotation_ids(srcTree)
        self.traverse_tree(srcTree, self.convert_one_tier)
        srcTree.xpath('/ANNOTATION_DOCUMENT/HEADER/'
                      'PROPERTY[@NAME=\'lastUsedAnnotationId\']')[0].text = str(self.lastUsedAID)
        srcTree.write(fnameTarget, encoding='utf-8', pretty_print=True)

    def convert_corpus(self):
        """
        Take every EAF file from the source directory subtree,
        convert it to ConLab format and store it in the target directory.
        """
        nFiles = 0
        for path, dirs, files in os.walk(self.srcDir):
            for fname in files:
                print(fname)
                if not fname.lower().endswith('.eaf'):
                    continue
                nFiles += 1
                srcPath = os.path.join(path, fname)
                targetPath = os.path.join(self.targetDir + path[len(self.srcDir):],
                                          fname)
                if srcPath == targetPath:
                    print('Error: scrPath == targetPath')
                    continue
                self.convert_file(srcPath, targetPath)
        print('Done,', nFiles, 'files converted.')


if __name__ == '__main__':
    convertor = ConLabEAFConvertor()
    convertor.convert_corpus()

