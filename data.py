import pandas as pd
import spacy
import string
from static.stopwords import stopwords
import nltk

class Data:
    def __init__(self, data):
        self.possible_errors = ["survey_error", "column_error", "extension_error"]
        self.errors = False
        self._is_tokenized_and_preprocessed = False
        self._is_processed = False
        self._is_selected = False
        self._is_example = False
        self.stopwords = stopwords # imported from static # should be private
        self.replacements = {"starytoken": "nowytoken"} # should be private
        self.top_words = None
        self.top_bigrams = None
        self.data = data # must be a dict; cols should be renamed with a class method to avoid naming issues in the future

    # DATA STATES
    def process(self):
        self._is_processed = True

    def select(self):
        self._is_selected = True

    def mark_as_example_data(self):
        self._is_example = True

    @property
    def is_selected(self):
        return self._is_selected
    
    @property
    def is_tokenized_and_preprocessed(self):
        return self._is_tokenized_and_preprocessed

    @property
    def is_processed(self):
        return self._is_processed

    @property
    def is_example(self):
        return self._is_example

    # ERROR HANDLING
    def display_error_message(self):
        if self.data == "survey_error":
            return "Podany numer ankiety nie istnieje"
        if self.data == "column_error":
            return "Podana kolumna nie istnieje"
        if self.data == "extension_error":
            return "Dopuszczalne rozszerzenia plików to .xlsx, .xls, .csv. i .txt"
        else:
            return "Wystąpił błąd"

    # DATA TRANSFORMATIONS
    def return_pandas_df(self):
        return pd.DataFrame(self.data)

    def display_original_text_as_html_table(self):
        try:
            return pd.DataFrame(self.data)[["id", "text"]].to_html()
        except:
            if self.data in self.possible_errors:
                return self.data
            else:
                return "Wystąpił błąd"
            

    def display_all_data_as_html_table(self):
        return pd.DataFrame(self.data).to_html()

    # DATA CLEANING AND PROCESSING
    # Adding / removing stopwords
    def add_remove_stopwords(self, words_to_add, words_to_remove): # takes inputs from forms as arguments

        words_to_add = words_to_add.split()
        words_to_remove = words_to_remove.split()
        # Append words to add
        for word in words_to_add:
            self.stopwords.append(word)
        # Filter out words to remove
        self.stopwords = [word for word in self.stopwords if word not in words_to_remove]

    # Replace problematic tokens
    def replace_tokens(self, replacements_string): # replacement_string comes from a form

        pairs = replacements_string.split()
        pairs = [pair.split("|") for pair in pairs]
        try:
            new_replacements = { pair[0]:pair[1] for pair in pairs }
        except:
            return 

        self.replacements.update(new_replacements)

    def display_replacements(self):
        pairs = [str(k) + "|" + str(v) for k, v in self.replacements.items()]
        return pairs
    
    @staticmethod
    def tokenize_and_lemmatize_with_spacy(texts):
        
        nlp = spacy.load("pl_core_news_lg")
        
        answers_lemmatized = []

        for text in texts:
            doc = nlp(text)
            lemmatized_tokens = [t.lemma_ for t in doc]
            answers_lemmatized.append(lemmatized_tokens)

        return answers_lemmatized

    def pre_process_corpus(self, texts):
        def remove_stop_punct_digits(tokens):
            punctuation = string.punctuation
            return [token.lower() for token in tokens if token not in self.stopwords and not token.isdigit() and token not in punctuation and len(token) > 1 and not token.isspace() ]
        return [remove_stop_punct_digits(text) for text in texts]

    def tokenize_and_clean(self):

        df = self.return_pandas_df()

        texts = list(df.text)
        texts = self.tokenize_and_lemmatize_with_spacy(texts)
        texts = self.pre_process_corpus(texts)

        df["tokens"] = texts
        df = df.loc[df.tokens.map(lambda x: len(x) > 0), ["text", "tokens"]] # odfiltrowuję puste, TU JESZCZE WARTO ODFILTROWAĆ NP. " "

        # .values returns Series as ndarray or ndarray-like depending on the dtype
        #original_docs = df["text"].values

        def replace_words(cell): # FUNCTION 2
            return [self.replacements.get(word, word) for word in cell]

        # replace words based on replacements dict
        df["tokens"] = df["tokens"].apply(lambda cell: replace_words(cell))

        #tokenized_docs = df["tokens"].values
        self.process()
        self.data = df.to_dict()

    # EXPLORATION
    def generate_top_tokens(self, ngram_type):

        df = self.return_pandas_df()

        if ngram_type == "words":

            top_tokens = df.explode("tokens") \
                .value_counts("tokens") \
                .head(15) \
                .rename_axis('top_tokens') \
                .reset_index(name="n")
            
            top_words = {"tokens": top_tokens["top_tokens"].tolist(),
                        "counts": top_tokens["n"].tolist() }
            
            return top_words
    

        if ngram_type == "bigrams":

            df["bigrams"] = df["tokens"].apply(nltk.bigrams)
            df["bigrams"] = df["bigrams"].apply(list)
            df_exploded = df.explode("bigrams", ignore_index=True)
            df_exploded = df_exploded[df_exploded["bigrams"].notna()]

            top_tokens = df_exploded.value_counts("bigrams") \
                .head(15) \
                .rename_axis('top_tokens') \
                .reset_index(name="n")
            
            top_bigrams = {"tokens": top_tokens["top_tokens"].tolist(),
                           "counts": top_tokens["n"].tolist() }
        
            return top_bigrams
        
        if ngram_type == "trigrams":

            df["trigrams"] = df["tokens"].apply(nltk.trigrams)
            df["trigrams"] = df["trigrams"].apply(list)
            df_exploded = df.explode("trigrams", ignore_index=True)
            df_exploded = df_exploded[df_exploded["trigrams"].notna()]

            top_tokens = df_exploded.value_counts("trigrams") \
                .head(10) \
                .rename_axis('top_tokens') \
                .reset_index(name="n")
            
            top_trigrams = {"tokens": top_tokens["top_tokens"].tolist(),
                           "counts": top_tokens["n"].tolist() }
        
            return top_trigrams
