import pickle
import pandas as pd
import json

# Flask imports
from flask import render_template, session, redirect, url_for, request, current_app, jsonify

# Load forms
from app.nlp.forms import (
    DataSelection, 
    ExampleData, 
    StopwordsForm, 
    ReplacementsForm,
    NgramsForm, 
    NetworkForm, 
    SelectedWordsForm, 
    ModelingForm, 
    DownloadResults, 
    ModelSelection, 
    LDACoherence, 
    LDAModel,
    NNMFModel,
    NNMFCoherence,
)

# Load classes
from app.nlp.data import Data
from app.nlp.nlp_models import LDA, NNMF, W2V #LSI
from app.nlp.storage import Storage

# Load functions
from app.nlp.auxiliary_modules.support_module import clear_cached_data
import app.nlp.auxiliary_modules.import_module as imp
import app.nlp.auxiliary_modules.network_module as net

from app.auth.routes import protect_access

import sqlalchemy as sa
from app import db
from app.nlp import bp

# === UTILITY FUNCTIONS ===

# Check for errors in data
def errors_in_data(d):
    if not isinstance(d.data, pd.DataFrame) and d.data in d.possible_errors:
        return True

# Initiate storage helper function
def initiate_storage():
    storage = session.get("storage")
    if not storage:
        storage = Storage()
        session["storage"] = storage
    return storage

def load_w2v_gensim_model():
    path_to_gensim_model = current_app.static_folder + "/word2vec/word2vec_gensim_nkjp_wiki_lemmas_all_300_cbow_hs.pickle"
    with open(path_to_gensim_model, 'rb') as gensim_model:
        word2vec = pickle.load(gensim_model)
    return word2vec

# === ROUTES ===

@bp.route("/sim_get_data_and_w2v", methods=["GET"])
#@protect_access
def sim_get_data_and_w2v():

    data = imp.load_example_data()
    d = Data(data)
    d.select()
    d.set_source("example")
    d.tokenize_and_clean()
    session["d"] = d

    return redirect(url_for("nlp.sim_w2v"))

@bp.route("/sim_w2v", methods=["GET"])
#@protect_access
def sim_w2v():

    d = session.get("d", redirect("nlp.sim_prepare_data"))

    storage = initiate_storage()
    word2vec = load_w2v_gensim_model()

    w2v = W2V("word2vec", d.data)
    w2v.vectorize_documents(word2vec)
    w2v.n_clusters = 20
    w2v.perform_mbkmeans()
    
    most_representative_terms = w2v.display_most_representative_terms(word2vec) # html
    display_summary = w2v.display_cluster_summary() # html
    results = w2v.display_results() # html

    storage.save_model(w2v)
    
    return f"""
    <html>
        <body>
            {display_summary}
            <br>
            {most_representative_terms}
            <br>
            {results}
        </body>
    </html>
    """

@bp.route("/sim_get_data_and_lda", methods=["GET"])
#@protect_access
def sim_get_data_and_lda():

    data = imp.load_example_data()
    d = Data(data)
    d.select()
    d.set_source("example")
    d.tokenize_and_clean()
    session["d"] = d

    return redirect(url_for("nlp.sim_lda"))

@bp.route("/sim_lda", methods = ["GET", "POST"])
#@protect_access
def sim_lda():

    d = session.get("d", redirect("nlp.get_data_and_lda"))
    storage = initiate_storage()

    lda = LDA("LDA", d.data) # initializing lda

    lda.create_nltk_dict()
    lda.create_corpus()

    lda.no_below=1
    lda.no_above=1
    lda.n_iterations=1000
    lda.n_clusters=20

    lda.create_model()
    lda_most_representative_words = lda.generate_most_representative_words()
    lda_most_representative_words_html = lda_most_representative_words.to_html(index=False)
        
    lda_summary = lda.generate_summary()
    lda_summary_html = lda_summary.to_html(index=False)

    storage.save_model(lda)
    session["storage"] = storage

    return f"""
    <html>
        <body>
            {lda_most_representative_words_html}
            <br>
            {lda_summary_html}
        </body>
    </html>
    """