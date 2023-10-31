from flask import send_file
from io import BytesIO
import xlsxwriter

from datetime import datetime

import numpy as np
from gensim.models import LdaModel, Nmf, LsiModel
from gensim.corpora import Dictionary # takes in a list of lists as argument
from gensim.models.coherencemodel import CoherenceModel
import pandas as pd

from sklearn.cluster import MiniBatchKMeans
from sklearn.metrics import silhouette_samples, silhouette_score
from sklearn.decomposition import PCA

# TODO Make sure that after data preprocessing, existing models will be reinitiated

# This class contains only basic features shared by all the models
# (including word2vec which is distinctly different from the rest)
class GeneralizedModel():
    def __init__(self, model_type, input_data):
        #self.input_data = input_data # this can probably be removed!
        # Explicit conversion of .values() objects to lists is necessary because .values() objs are not pickable
        # See for example: https://github.com/tensorflow/models/issues/4780 
        self._model_type = model_type 
        self.list_of_tokenized_docs = list(input_data["tokens"].values()) # input_data["tokens"] returns a dict (key-value pairs)
        self.list_of_original_docs = list(input_data["text"].values())
        self.list_of_ids = list(input_data["tokens"].keys())
        self.n_clusters = 10
        self.cluster_assignments = []
        self.coherence_scores = {}
        self.current_model = None
        self._created_at = datetime.now()
    
    @property
    def model_type(self):
        return self._model_type
    
    @property
    def created_at(self):
        return self._created_at


# LDA class. This class serves as the basis for all the other nltk models
# (i.e. NNMF and LSI)
# W2V, because of its uniqueness, inherits direclty from the generalizedModel class
class LDA(GeneralizedModel):
    def __init__(self, model_type, input_data):
        super().__init__(model_type, input_data)
        self.no_below = 5
        self.no_above = .5
        self.n_iterations = 600
        self.n_comp_iterations = 250
        self.id2word = None # set when create_corpus() runs for the first time
        self.nltk_dictionary = self.create_nltk_dict()
        self.corpus = self.create_corpus()
    
    # CREATE MODEL
    def create_model(self):
        '''
        Creates an LDA model, saves it in class properties and 
        updates cluster allocation of individual observations.
        '''
        model = LdaModel(
            corpus=self.corpus, 
            id2word=self.id2word, 
            iterations=self.n_iterations, 
            num_topics=self.n_clusters
            )
        
        self.current_model = model
        self.assign_top_topics() # update cluster allocations

    # PRESENTATION
    def assign_top_topics(self):
        
        document_topics = self.get_document_topics()

        most_probable_topics = []
        for doc in document_topics:
            doc_as_dict = dict(doc)
            try:
                most_probable_topic = max(doc_as_dict, key=doc_as_dict.get) # TODO Decide what to do with ties
                most_probable_topics.append(most_probable_topic)
            except ValueError:
                most_probable_topics.append(None)
        
        self.cluster_assignments = most_probable_topics
        return most_probable_topics

    def get_document_topics(self):
        document_topics = self.current_model.get_document_topics(
                                bow = self.corpus, # bag of words
                                minimum_probability = 0,
                                minimum_phi_value = None,
                                per_word_topics = False
                                )
    
        return document_topics

    def generate_document_topics_table(self):

        document_topics = self.get_document_topics()

        probs = []
        for doc in document_topics:
            topic_probs = []
            for topic_prob in doc:
                topic_probs.append(topic_prob[1])
            probs.append(topic_probs)

        df = pd.DataFrame(data=probs)
        df.insert(loc=0, column='tokenized_text', value=self.list_of_tokenized_docs)
        df.insert(loc=0, column='original_text', value=self.list_of_original_docs)
        df.insert(loc=0, column='top_topic', value=self.cluster_assignments)
        df.insert(loc=0, column='id', value=self.list_of_ids)

        df = df.sort_values(by=["top_topic"])

        return df

    def generate_summary(self):
        '''
        Generates a pandas df containing a summary of results.
        Columns:
        row index | id | tokenized_text | original_text | top_topic | cluster probs ...
        The table is grouped by the top_topic column.
        Only 5 observations for each top_topic are displayed.
        '''
        summary = (self.generate_document_topics_table()
         .groupby("top_topic")
         .head(5))
        
        return summary

    # COMPARE COHERENCE
    def compare_coherence(self, start, end, step):
        '''
        Ouputs coherence scores for selected n of ks with a step specified.
        By default uses low number of iterations (from self.n_comp_iterations) to speed up calculations.
        Currently, the default n of iterations is below the recommended level.
        '''
        self.create_nltk_dict()
        self.create_corpus()

        coherence_scores = []
        ks = []

        for k in range(start, end, step):
            model = LdaModel(corpus=self.corpus, id2word=self.id2word, iterations = self.n_comp_iterations, num_topics=k)
            coherence_model = CoherenceModel(model=model, corpus=self.corpus, dictionary=self.nltk_dictionary, coherence='u_mass')
            coherence_score = coherence_model.get_coherence()
            coherence_scores.append(coherence_score)
            ks.append(k)
        
        self.coherence_scores = {"scores": coherence_scores,
                                 "ks": ks}
    
    def create_nltk_dict(self):
        '''
        Transforms original documents into an nltk dictionary object.
        This is necessary to perform operations such as filtering outliers
        (e.g. very (in)frequent words.) and to create a corpus of documents 
        transformed into bags of words (see below).
        '''
        nltk_dict = Dictionary(self.list_of_tokenized_docs)
        nltk_dict.filter_extremes(no_below=self.no_below, no_above=self.no_above)
        self.nltk_dictionary = nltk_dict
        return nltk_dict

    def create_corpus(self):
        '''
        Creates a tokenized corpus where each original document is transformed into a bag of words.
        Creates pairings of numerical word ids and actual words and stores them in self.id2word.
        '''

        corpus = [self.nltk_dictionary.doc2bow(doc) for doc in self.list_of_tokenized_docs]
        self.corpus = corpus
        temp = self.nltk_dictionary[0] # This is only to "load" the dictionary (??)
        id2word = self.nltk_dictionary.id2token
        self.id2word = id2word

# =============
# NNMF
# =============

class NNMF(LDA):

    def create_model(self): 
        self.create_nltk_dict()
        self.create_corpus()
        
        model = Nmf(corpus=self.corpus, id2word=self.id2word, num_topics=self.n_clusters)
        self.current_model = model
        self.assign_top_topics()
    
    def compare_coherence(self, start, end, step):
        self.create_nltk_dict()
        self.create_corpus()

        coherence_scores = []
        ks = []

        for k in range(start, end, step):
            model = Nmf(corpus=self.corpus, id2word=self.id2word, num_topics=k)
            coherence_model = CoherenceModel(model=model, corpus=self.corpus, dictionary=self.nltk_dictionary, coherence='u_mass')
            coherence_score = coherence_model.get_coherence()
            coherence_scores.append(coherence_score)
            ks.append(k)
        
        self.coherence_scores = {"scores": coherence_scores,
                                 "ks": ks}
        
    def get_document_topics(self):
        document_topics = self.current_model.get_document_topics(
            bow = self.corpus, 
            minimum_probability = 0,
            normalize=True)
        return document_topics
    
    def generate_document_topics_table(self):

        probs = []
        for doc in self.get_document_topics():
            list_of_0s = [0 for i in range(0,self.n_clusters,1)]
            for tup in doc:
                list_of_0s[tup[0]] = tup[1]
            probs.append(list_of_0s)

        df = pd.DataFrame(data=probs)
        df.insert(loc=0, column='top_topic', value=self.cluster_assignments)
        df.insert(loc=0, column='text', value=self.list_of_tokenized_docs)
        df.insert(loc=0, column='id', value=self.list_of_ids)

        df = df.sort_values(by=["top_topic"])

        return df

# =============
# LSI
# =============

class LSI(LDA):

    def create_model(self):
        model = LsiModel(corpus=self.corpus, id2word=self.id2word, num_topics=self.n_clusters)
        self.current_model = model
    
    def compare_coherence(self, start, end, step):
        self.create_nltk_dict()
        self.create_corpus()

        coherence_scores = []
        ks = []

        for k in range(start, end, step):
            model = LsiModel(corpus=self.corpus, id2word=self.id2word, num_topics=k)
            coherence_model = CoherenceModel(model=model, corpus=self.corpus, dictionary=self.nltk_dictionary, coherence='u_mass')
            coherence_score = coherence_model.get_coherence()
            coherence_scores.append(coherence_score)
            ks.append(k)
        
        self.coherence_scores = {"scores": coherence_scores,
                                 "ks": ks}
        
    def show_topics(self):
        return self.current_model.show_topics()

# ==============
# W2V
# ==============

class W2V(GeneralizedModel):

    def __init__(self, model_type, input_data):
        super().__init__(model_type, input_data)
        self.documents_as_vectors = None
        self.kmeans = None
        self.pca_n_of_pcs = 20
        self.pca_vectors = None
        self.pca_variance_explained = np.array([])
        self.pca_vectors_standardized = False

    def vectorize_documents(self, word2vec):

        features = []

        for tokens in self.list_of_tokenized_docs:
            # creates a vector of zeros equal to the w2v vector size
            zero_vector = np.zeros(word2vec.vector_size)
            vectors = []
            for token in tokens:
                if token in word2vec: # replace tokens with KeyedVector object
                    try:
                        vectors.append(word2vec[token]) # return w2v object (a vector) 
                    except KeyError:
                        continue
            if vectors:
                vectors = np.asarray(vectors)
                avg_vec = vectors.mean(axis=0)
                features.append(avg_vec)
            else:
                # replace missing vectors with the zero vector
                features.append(zero_vector)
            
            self.documents_as_vectors = features

        return features # TODO Probably to be removed

    def perform_pca(self, standardize):

        pca = PCA(n_components=self.pca_n_of_pcs)

        # numeric vectors of pc scores
        fitted_pca = pca.fit_transform(self.documents_as_vectors)
        
        self.documents_as_vectors = fitted_pca
        self.pca_variance_explained = pca.explained_variance_ratio_

    def standardize_pcs(self):

        df = pd.DataFrame(self.pca_vectors)
        df = (df - df.mean()) / df.std()
        standardized_pcs = df.values.tolist()
        
        self.pca_vectors = standardized_pcs
        self.pca_vectors_standardized = True
    
    def display_pcs(self):
        
        # Create df with sil values for clusters
        df = pd.DataFrame(self.pca_variance_explained)
        df.reset_index(inplace=True)
        df = df.rename(columns = {'index':'cluster'})
        print(df)
    
    def perform_mbkmeans(self):
        
        matrix = pd.DataFrame(self.documents_as_vectors)
        kmeans = MiniBatchKMeans(n_clusters=self.n_clusters, batch_size=500).fit(matrix)
        self.kmeans = kmeans
        self.cluster_assignments = kmeans.labels_

    def generate_cluster_summary(self):

        matrix = pd.DataFrame(self.documents_as_vectors)
        sample_silhouette_values = silhouette_samples(matrix, self.kmeans.labels_)
        
        silhouette_values = []
        for i in range(self.n_clusters):
            cluster_silhouette_values = sample_silhouette_values[self.kmeans.labels_ == i]
            silhouette_values.append(
                (
                    i,
                    cluster_silhouette_values.shape[0],
                    cluster_silhouette_values.mean(),
                    cluster_silhouette_values.min(),
                    cluster_silhouette_values.max(),
                )
            )

        cluster_information = pd.DataFrame(silhouette_values, columns=["index", "size", "mean_sil", "min_sil", "max_sil"])
        cluster_information.reset_index(drop = True, inplace=True)
        cluster_information = cluster_information.rename(columns = {'index':'cluster'})
        
        return cluster_information # pandas df

    def display_cluster_summary(self):
        summary = self.generate_cluster_summary()
        return summary.to_html(index=False)
    
    def generate_results_table(self):
        results_table = pd.DataFrame({"id": self.list_of_ids,
                                     "cluster": self.cluster_assignments,
                                     "original_text": self.list_of_original_docs,
                                     "tokenized_docs": self.list_of_tokenized_docs})
        return results_table
    
    def display_results(self):
        results = (self.generate_results_table()
                   .sort_values(by="cluster")
                   .groupby("cluster")
                   .head(5)
                   .to_html(index=False))
        
        return results

    def generate_most_representative_terms(self, word2vec):

        cluster_number = []
        list_of_terms = []

        for i in range(self.n_clusters):
            tokens_per_cluster = ""
            most_representative = word2vec.most_similar(positive=[self.kmeans.cluster_centers_[i]], topn=10)
            for t in most_representative:
                tokens_per_cluster += f"{t[0]} "
            list_of_terms.append(tokens_per_cluster)
            cluster_number.append(i)

        df = pd.DataFrame({"cluster":cluster_number, "terms":list_of_terms})

        return df
    
    def display_most_representative_terms(self, word2vec):
        terms = self.generate_most_representative_terms(word2vec).to_html(index=False)
        return terms
    
    @classmethod
    def write_to_excel(self, word2vec, model):
        
        output = BytesIO()

        if model.pca_variance_explained.size == 0:
            most_representative_terms = model.generate_most_representative_terms(word2vec)
        summary = model.generate_cluster_summary()
        results = model.generate_results_table()

        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            summary.to_excel(writer, sheet_name='summary', index=False)
            if model.pca_variance_explained.size == 0:
                most_representative_terms.to_excel(writer, sheet_name='most_representative_terms', index=False)
            results.to_excel(writer, sheet_name='results', index=False)
        # TODO add pc values to the excel file
        output.seek(0)

        return send_file(output, download_name='results.xlsx')
