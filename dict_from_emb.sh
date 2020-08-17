SRC_ISO='eng'
TRG_ISO='npi'
SRC_EMB=/PATH/TO/SRC/EMB.VEC
TRG_EMB=/PATH/TO/TRG/EMB.VEC
N=1000
OUTPUT=./${SRC_ISO}2${TRG_ISO}.emb.txt
python ./lexicon_from_embeddings.py $SRC_EMB $TRG_EMB $SRC_ISO $TRG_ISO $OUTPUT --N $N --min_char_len 1 --batch_size 1000 --filter_stopwords
