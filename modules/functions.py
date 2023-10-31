import spacy
import re
import string
import gensim
from gensim.models import Word2Vec

### =============================
# Data pre-processing
### =============================

# This function is currently not utilized
# Move some of it to Data
def clean_text(text, tokenizer, stopwords):
    """Pre-process text and generate tokens

    Args:
        text: Text to tokenize.

    Returns:
        Tokenized text.
    """
    text = str(text).lower()  # Lowercase words
    text = re.sub(r"\[(.*?)\]", "", text)  # Remove [+XYZ chars] in content
    text = re.sub(r"\s+", " ", text)  # Remove multiple spaces in content
    text = re.sub(r"\w+…|…", "", text)  # Remove ellipsis (and last word)
    text = re.sub(r"(?<=\w)-(?=\w)", " ", text)  # Replace dash between words
    text = re.sub(
        f"[{re.escape(string.punctuation)}]", "", text
    )  # Remove punctuation

    tokens = tokenizer(text)  # Get tokens from text
    #tokens = [t for t in tokens if not t in stopwords]  # Remove stopwords
    #tokens = ["" if t.isdigit() else t for t in tokens]  # Remove digits
    #tokens = [t for t in tokens if len(t) > 1]  # Remove short tokens
    return tokens

#pl = spacy.load("pl_core_news_lg")
#stopwords_pl = sorted(list(pl.Defaults.stop_words))
nlp = spacy.load("pl_core_news_lg") # ???

### ======
# Modeling
### ======

# These are not utilized
def train_new_model():
    model_trained_on_data = Word2Vec(sentences=tokenized_docs, vector_size=100, workers=1)
    return model_trained_on_data

def load_pretrained_model():
    pretrained_model = gensim.models.KeyedVectors.load_word2vec_format("static/word2vec/nkjp_lemmas_all_100_cbow_hs.txt")
    return pretrained_model