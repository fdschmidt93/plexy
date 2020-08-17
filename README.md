# plexy

plexy is small utility to automatically retrieve dictionaries between any two available languages from [PanLex](https://panlex.org/). PanLex is a panlingual lexicon, comprising 2,500 across 5,700 languages. Thus, the tool for instance facilitates rapidly constructing seeding supervision dictionaries for inducing mappings to align word embeddings cross-lingually between any two languages covered by PanLex. For convenience, plexy can query PanLex from both lists of words and words in word2vec-formatted embeddings.

## Features
* Construct dictionaries between any two languages (and dialects thereof) swiftly
* Retrieve one-to-many translations
* Control translation quality by setting minimum quality thresholds 

## Usage

ISO 639-3 language codes are available [here](https://iso639-3.sil.org/code_tables/639/data). Note, you should generally set to the most generic language codes and plexy for now defaults to retrieving from the most common 'variant' (cf. dialects) of a language.


### Variant A: Construct a lexicon from a word list
```
Generate seeding dictionary with PanLex

optional arguments:
  --list PATH           Path to source language word list
  --src ISO             ISO 639-3 language code of source language
  --trg ISO             ISO 639-3 language code of target language
  --k k                 top-k translations,
  --qual INT            Lower bound of translation quality
  --output PATH         Path to store txt, default: ./$src2$trg.txt
  --log PATH            Path to store output log
  --inline              If k>1, write translations inline
  --timeout_idx TIMEOUT_IDX
                        Timeout (s) to get src lang identifiers for trg lang query, default=5
  --timeout_trans TIMEOUT_TRANS
                        Timeout (s) to query trg lang translations, default=30s
  --batch_size BATCH_SIZE
                        Batch size for queries, default=200
  --warning             Print all source tokens w/o translation
```
See `./dict_from_list.sh` for an example.

### Variant B: Construct a lexicon from word embeddings
```

positional arguments:
  PATH                  Path to source embeddings, stored word2vec style
  PATH                  Path to target embeddings, stored word2vec style
  ISO                   ISO 639-3 language code of source language
  ISO                   ISO 639-3 language code of target language
  PATH                  Path to write dictionarty tab-delimited

optional arguments:
  --qual INT            Lower bound of translation quality, low: 5-15 (high: c.50) for
                        distant (close) langauges (default: 5)
  --N N                 Maximum number of pairs to store, -1 for all found (default: -1)
  --batch_size N        Batch size for requests to PanLex, default recommended (default:
                        1000)
  --filter_stopwords    If src_iso is English, filter stop words and words shorter than 3
                        chars (default: False)
  --min_char_len MIN_CHAR_LEN
                        Minimum source length token length to accept into dictionary,
                        potential lazy filter (default: 0)
  --log path            Store induction log at PATH (default: ./debug.txt)
  --warnings            Indicate whether a pair of tokens cannot be resolved (default:
                        False)
```
See `./dict_from_emb.sh` for an example.

Be mindful that constructing dictionaries from word embeddings is more restrictive by design:
* Only the top candidate is returned
* Query results are resolved against by intermediate lower case comparison to embedding tokens

## Caveats
The PanLex API can only turn 2,000 generic results at a time. As a consequence, should you for instance construct dictionaries for high-resource languages, be mindful to set small batch sizes with a balanced threshold, as that effectively drives the number of results. Too large batch sizes at too low thresholds lead to cut off return values, which may not cover all tokens accordingly. That said, longer timeouts may alleviate the issue, though the choice of best (fastest) parameters highly depends on the individual retrieval scenario. Conclusively, conservative parameters are recommended.

## Requirements

* Requests

## Contact

**Author:** Fabian David Schmidt\
**Affiliation:** University of Mannheim\
**E-Mail:** fabian.david.schmidt@hotmail.de
