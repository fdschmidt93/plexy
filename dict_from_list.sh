#!usr/bin/bash
SRC_LANG=eng
TRG_LANG=deu
TOKENS=./samples/english.sample-input.txt
k=1
out=./eng2deu.sample-output.txt
python ./lexicon_from_list.py --list $TOKENS --src $SRC_LANG --trg $TRG_LANG --k $k --qual 0 --batch_size 50
