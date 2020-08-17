import argparse
import logging
from typing import List, Tuple

from lexicon_from_list import induce_lexicon
from src.utils import read_emb, to_batches, write_lexicon


logger = logging.getLogger(__name__)

def get_parser():
    parser = argparse.ArgumentParser(
            description='Dictionary Retrieval with PanLex from Embeddings',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    # input
    parser.add_argument('src_emb', metavar='PATH', type=str,
                        help='Path to source embeddings, stored word2vec style')
    parser.add_argument('trg_emb', metavar='PATH', type=str,
                        help='Path to target embeddings, stored word2vec style')
    parser.add_argument('src_iso', metavar='ISO', type=str,
                        help='ISO 639-3 language code of source language')
    parser.add_argument('trg_iso', metavar='ISO', type=str,
                        help='ISO 639-3 language code of target language')
    # input
    parser.add_argument('output', metavar='PATH', type=str,
                        help='Path to write dictionarty tab-delimited')
    # query parameters
    parser.add_argument('--qual', metavar='INT', type=int, default=5,
                        help="""Lower bound of translation quality,
                                low: 5-15 (high: c.50) for distant (close) langauges""")
    parser.add_argument('--N', metavar='N', type=int, default=-1,
                        help='Maximum number of pairs to store, -1 for all found')
    parser.add_argument('--batch_size', metavar='N', type=int, default=1000,
                        help='Batch size for requests to PanLex, default recommended')
    parser.add_argument('--filter_stopwords', action='store_true',
                        help='If src_iso is English, filter stop words and words shorter than 3 chars')
    parser.add_argument('--min_char_len', type=int, default=0,
                        help='Minimum source length token length to accept into dictionary, potential lazy filter')
    # logging
    parser.add_argument('--log', metavar='path', type=str, default='./debug.txt',
                        help='Store induction log at PATH')
    parser.add_argument('--warnings', action='store_true',
                        help='Indicate whether a pair of tokens cannot be resolved')
    return parser.parse_args()

def setLogger(args: argparse.Namespace):
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


def intersect(src2trg: dict,
              src: List[str],
              trg: List[str],
              args: argparse.Namespace) -> List[Tuple[str,str]]:
    """
    Resolve token lists from embeddings with PanLex dictionary.

    :param src2trg dict: PanLex dictionary
    :param src List[str]: list of tokens from source embeddings
    :param trg List[str]: list of tokens from token embeddings
    :param args argparse.Namespace: CLI arguments
    :rtype List[Tuple[str,str]]: pairs of tokens
    """
    out = []
    src_lower = [w.lower() for w in src]
    trg_lower = [w.lower() for w in trg]
    # for k, v in src2trg.items():
    for src_word, trg_word in src2trg.items():
        try:
            i = src_lower.index(src_word.lower())
            j = trg_lower.index(trg_word.lower())
            out.append((src[i], trg[j]))
        except ValueError:
            if args.warnings:
                logger.warning(f'{src_word} - {trg_word} is not in original dictionary')
    return out

def check_dictionary(src2trg: dict) -> dict:
    """
    Check validity of PanLex dictionary:
        - Each source token only has one target token
        - Source and target tokens are strings

    :param src2trg dict: PanLex dictionary
    :rtype dict: validated PanLex dictionary
    """
    out = {}
    for k, v in src2trg.items():
        assert isinstance(k, str)
        assert len(v) == 1
        assert isinstance(v[0], str)
        out[k] = v[0]
    return out

def filter_dictionary(src2trg: dict, args: argparse.Namespace) -> List[Tuple[str,str]]:
    """
    If English is main langauge, focus on tokens with more semantic meaning by
    filtering out stop words from mapping training dictionary.
    '
    :param src2trg dict: English: target language token dictionary
    """
    out = []
    filter_symbols = []
    if args.filter_stopwords:
        try:
            from nltk.corpus import stopwords
            stop_words = stopwords.words('english')
            filter_symbols.extend(stop_words)
        except ModuleNotFoundError:
            logger.info(f'Please install NLTK to remove stopwords')
    if args.min_char_len or filter_symbols:
        for src_, trg_ in src2trg:
            if src_ in filter_symbols:
                continue
            elif len(src_) <= args.min_char_len:
                continue
            else:
                out.append((src_, trg_))
        return out
    # only reachable if min_char_len or symbols are not set
    return list(src2trg.items())

def clean_up(words: List[str]) -> List[str]:
    """
    PanLex query may fail given the below tokens.

    The issue probably can be fixed if symbols are properly escaped
    though more often we would not want to include symbols anyways.
    """
    SYMBOLS = '!"#$%&()*+,-./:;<=>?@[\\]^_`{|}~\t\n'
    for sym in SYMBOLS:
        if sym in words:
            words = [w for w in words if w != sym]
    return words

def main():
    args = get_parser()
    setLogger(args)
    # Log config
    logger.info(f'============ Config')
    for arg in vars(args):
        logger.info(f'{arg}: {getattr(args, arg)}')

    src_words, trg_words = read_emb(args.src_emb, args.trg_emb)

    # filter out json format quirk
    src_words = clean_up(src_words)
    pairs = []
    logger.info(f'============ Retrieving Translations')
    for i, words_batch in enumerate(to_batches(src_words, batch_size=args.batch_size)):
        try:
            # breakpoint()
            src2trg = induce_lexicon(words_batch, src=args.src_iso, trg=args.trg_iso, k=1, qual=args.qual, batch_size=min(len(words_batch), args.batch_size))
            src2trg = check_dictionary(src2trg)
            src2trg = intersect(src2trg, src_words, trg_words, args)
            src2trg = filter_dictionary(src2trg, args)
            pairs.extend(src2trg)
            logger.info(f'{len(pairs)} word translation identified after {i} batches')
        except:
            logger.warning(f'Passing batch {i} -- (likely) caused by faulty string encoding in request')
        if len(pairs) >= args.N and args.N != -1:
            break
    if args.N != -1:
        pairs = pairs[:args.N] 

    logging.info(f'============ Writing to disk')
    with open(args.output, 'w') as file:
        for pair in pairs:
            left, right = pair
            line = f'{left}\t{right}\n'
            file.write(line)

if __name__ == '__main__':
    main()
