import requests
import nltk
import re
from collections import Counter
from bs4 import BeautifulSoup
from stop_words import stops


def count_and_save_words(url):
    errors = []

    try:
        r = requests.get(url)
    except:
        errors.append(
            "Unable to get URL. Please make sure it's valid and try again."
        )
        return {"error": errors}

    # text processing
    raw = BeautifulSoup(r.text, features="html.parser").get_text()
    nltk.data.path.append('./nltk_data/')  # set the path
    tokens = nltk.word_tokenize(raw)
    text = nltk.Text(tokens)

    # remove punctuation, count raw words
    nonPunct = re.compile('.*[A-Za-z].*')
    raw_words = [w for w in text if nonPunct.match(w)]
    raw_word_count = Counter(raw_words)

    # stop words
    no_stop_words = [w for w in raw_words if w.lower() not in stops]
    no_stop_words_count = Counter(no_stop_words)

    return url, raw_word_count, no_stop_words_count
    # # save the results
    # try:
    #     result = Result(
    #         url=url,
    #         result_all=raw_word_count,
    #         result_no_stop_words=no_stop_words_count
    #     )
    #     db.session.add(result)
    #     db.session.commit()
    #     return result.id
    # except:
    #     errors.append("Unable to add item to database.")
    #     return {"error": errors}
