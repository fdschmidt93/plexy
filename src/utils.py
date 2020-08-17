def read_list(path: str):
    """
    Read UTF-8 encoded word list from path.

    Example file:
    house
    play
    train
    ...

    :param path str: file path to utf-8 word list

    """
    with open(path, 'r') as file:
        word_list = []
        for line in file:
            word_list.append(line.strip())
        return word_list

def write_lexicon(path: str, src2trg: dict, separator: str='\t', inline: bool=False):
    """
    Write translation lexicon to utf-8 text file.

    Example (inline False):
    hello    hallo
    train    Zug
    train    trainieren
    ...

    Example (inline True):
    hello    hallo
    train    Zug,trainieren
    ...

    :param path str: path to txt file
    :param src2trg dict: input lexicon
    :param separator str: separator character between source and target words
    :param inline boolean: write multiple translations inline
    """
    with open(path, 'w') as file:
        for src, trg in src2trg.items():
            line = f'{src}{separator}' 
            if len(trg) == 1:
                line += f'{trg[0]}\n'
                file.write(line)
            elif len(trg) > 1:
                if inline:
                    line += f'{",".join(trg)}\n'
                    file.write(line)
                else:
                    for trans in trg:
                        file.write(line + f'{trans}\n')

def to_batches(iterable: list, batch_size:int=1):
    """
    Yield batch from Python iterables.

    :param iterable iterable: Python iterable
    :param batch_size int: slice iterable into batches of batch_size
    """
    l = len(iterable)
    for ndx in range(0, l, batch_size):
        yield iterable[ndx:min(ndx + batch_size, l)]

def read_emb(src_path: str, trg_path: str, pass_header: bool=True, top_tokens: int=50_000):
    """
    Read tokens of word2vec style embeddings to List[str].

    :param src_path str: path to word2vec-style source language embeddings
    :param trg_path str: path to word2vec-style target language embeddings
    :param top_tokens int: restrict read tokens to top 50_000 tokens
    """
    def get_tokens(path):
        word_list = []
        with open(path, 'r') as file:
            # pass header
            if pass_header:
                next(file)
            for i, line in enumerate(file):
                if i < top_tokens:
                    word = line.split(' ')[0]
                    word_list.append(word)
                else:
                    break
        assert len(word_list) == top_tokens
        return word_list
    src_words = get_tokens(src_path)
    trg_words = get_tokens(trg_path)
    return (src_words, trg_words)
