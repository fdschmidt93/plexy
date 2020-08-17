import argparse
from functools import wraps, partial
import logging
import math
import time

from typing import Union, List
from src.utils import read_list, write_lexicon, to_batches

import requests

# PanLex Terminology
# expr: expression, identifier for a word
# variety: sub-category of a certain language, with 000 denoting most general form
# trans_qual: score estimated from intertwinedness of languages (e.g. quantifiyng distance in hops) def read_list(path):

logger = logging.getLogger(__name__)

def get_parser():
    parser = argparse.ArgumentParser(description='Generate seeding dictionary with PanLex')
    parser.add_argument('--list', metavar='PATH', type=str, required=True,
                        help='Path to source language word list')
    parser.add_argument('--src', metavar='ISO', type=str, required=True,
                        help='ISO 639-3 language code of source language')
    parser.add_argument('--trg', metavar='ISO', type=str, required=True,
                        help='ISO 639-3 language code of target language')
    parser.add_argument('--k', metavar='k', type=int, default=1,
                        help='top-k translations, ')
    parser.add_argument('--qual', metavar='INT', type=int, default=5,
                        help="""Lower bound of translation quality""")
    parser.add_argument('--output', metavar='PATH', type=str,
                        help='Path to store txt, default: ./$src2$trg.txt')
    parser.add_argument('--log', metavar='PATH', type=str, default='./debug.list.txt',
                        help='Path to store output log')
    parser.add_argument('--inline', action='store_true',
                        help='If k>1, write translations inline')
    parser.add_argument('--timeout_idx', type=int, default=5,
                        help='Timeout (s) to get src lang identifiers for trg lang query, default=5')
    parser.add_argument('--timeout_trans', type=int, default=30,
                        help='Timeout (s) to query trg lang translations, default=30s')
    parser.add_argument('--batch_size', type=int, default=200,
                        help='Batch size for queries, default=200')
    parser.add_argument('--warning', action='store_true',
                        help='Print all source tokens w/o translation')
    return parser.parse_args()


def batched(func):
    """Batched execution of get_id2expr and get_translations."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        description = None
        input_ = None
        out = {}
        batch_size = None
        if 'get_translations' == func.__name__:
            # d = 5 # c. 5 results per translation
            input_ = kwargs.pop('expr_id', None)
            batch_size = kwargs.pop('batch_size', None)
            logger.info('=============== Retrieving expression identifiers')
        elif 'get_id2expr' == func.__name__:
            input_ = kwargs.pop('word', None)
            logger.info('=============== Requesting translations')
            batch_size = kwargs.pop('batch_size', None)
        batch_size = batch_size if batch_size is not None else 200
        if input_ is not None:
            batch_count = math.ceil(len(input_) / batch_size)
            for i, b in enumerate(to_batches(input_, batch_size=batch_size), 1):
                logger.info(f'Batch {i} of {batch_count} processed!')
                out = {**out, **func(b, **kwargs)}
                # 2 queries / second
                time.sleep(0.5)
        return out
    return wrapper


@batched
def get_id2expr(word: Union[str, List[str]], src: str, timeout: int=5, batch_size: int=200) -> dict:
    """
    Fetch expression identifier for input word(s).

    :param word str/list[str]: words to translate
    :param src str: ISO 639 code for source language
    :param timeout int: TODO
    """
    # -000: pull most common language variety
    src_lang = src + "-000"
    # convert to json array of strings format
    if isinstance(word, list):
        word = '","'.join(word)
        word = '["' + word + '"]'
    elif isinstance(word, str):
        word = f'"{word}"'
    data = (f'{{"txt": {word}, '
            f'"uid": "{src_lang}"}}').encode('utf-8')
    try:
        response = requests.post('http://api.panlex.org/v2/expr', data=data, timeout=timeout)
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(f'Request return {err}')
        raise
    results = response.json()['result']
    id2expr = {result['id']: result['txt'] for result in results}
    return id2expr

@batched
def get_translations(expr_id: List[int], trg: str, trans_qual_min: int=50, timeout: int=30, batch_size: int=200) -> dict:
    """
    Request translation(s) for expression id in target language.

    :param expr_id int: unique identifier for a word
    :param trg str: ISO 639 code for the target language
    :param trans_qual_min int: minimum threshold of translation quality score
    :return expr2trans dict: {expr_id: {trans_quality: [trans_1, ..., trans_n]}
    """
    # -000: pull most common language variety
    trg_lang = trg + "-000"
    data = (f'{{"include": "trans_quality", '
            f'"trans_expr": {expr_id}, '
            f'"uid": "{trg_lang}", '
            f'"trans_quality_min": {trans_qual_min}}}')
    response = requests.post('http://api.panlex.org/v2/expr', data=data, timeout=timeout)
    results = response.json()['result']
    # expr2trans >> {expr: {trans_quality: [txt_1, ..., txt_n]}
    expr2trans = {}
    for result in results:
        trans_expr = result['trans_expr']
        trans_quality = result['trans_quality']
        txt = result['txt']
        if not trans_expr in expr2trans:
            expr2trans[trans_expr] = {}
        if not trans_quality in expr2trans[trans_expr]:
            expr2trans[trans_expr][trans_quality] = []
        expr2trans[trans_expr][trans_quality].append(txt)
    return expr2trans

def filter_translations(expr2trans: dict, top_k: int) -> dict:
    expr2top_k = {}
    for expr, trans in expr2trans.items():
        """
        Retain only top-k translations.

        top-k translations are evaluated according to the PanLex translation
        quality score.

        Mind arbitrary cut-off of potential overhang.

        :param expr2trans dict: {expr_id: {trans_qual: ['trans_1', ..., 'trans_n'}}
        :param top_k int: # translations to retain
        """
        trans_scores = sorted(trans.keys())
        trans_expr = []
        while trans_scores and len(trans_expr) < top_k:
            score = trans_scores.pop()
            trans_candidates = trans[score]
            trans_expr.extend(trans_candidates)
        # too many candidates may be added, simple workaround
        trans_expr = trans_expr[:top_k]
        expr2top_k[expr] = trans_expr
    return expr2top_k

def induce_lexicon(words: Union[str, List[str]], src: str, trg: str, k: int, qual: int, batch_size: int=200) -> dict:
    """
    Generate lexicon of list of input words from source to target language.

    :param words str/list[str]: words to translate
    :param src str: ISO 639 code of source language
    :param trg str: ISO 639 code of target language
    :param k int: top-k translations to retain
    :param qual int: lower bound of translation quality score
    """
    id2expr = get_id2expr(word=words, src=src, batch_size=batch_size)
    expr2id = {e:i for i, e in id2expr.items()}
    expr_id = list(id2expr.keys())
    expr2trans = get_translations(expr_id=expr_id, trg=trg, trans_qual_min=qual, batch_size=batch_size)
    expr2trans = filter_translations(expr2trans, top_k=k)
    src2trg = {id2expr[k]: v for k, v in expr2trans.items()}


    return src2trg
def setLogger(args):
    """Configure basic logger."""
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    formatter = logging.Formatter('%(asctime)s - %(message)s')

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # Setup file logging as well
    fh = logging.FileHandler(args.log)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

def main():
    args = get_parser()
    setLogger(args)
    # Log config
    logger.info(f'============ Config')
    for arg in vars(args):
        logger.info(f'{arg}: {getattr(args, arg)}')

    if args.output is None:
        args.output = f'{args.src}2{args.trg}.txt'
    words = read_list(path=args.list)
    src2trg = induce_lexicon(words=words, src=args.src, trg=args.trg,
                             k=args.k, qual=args.qual, batch_size=args.batch_size)
    if len(words) > len(src2trg):
        logger.warning('=============== Missing words')
        logger.warning(f'No match for {len(words)-len(src2trg)} words')
        if args.warning:
            not_found = [tok for tok in words if tok not in src2trg]
            logger.warning(not_found)
    write_lexicon(args.output, src2trg, inline=args.inline)

if __name__ == '__main__':
    main()
