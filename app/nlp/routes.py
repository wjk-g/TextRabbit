import pickle
import pandas as pd
import json

# Flask imports
from flask import render_template, session, redirect, url_for, request, current_app

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

# === HOME ===


@bp.route("/home", methods=["GET", "POST"])
@protect_access
def home():
    d = session.get("d", Data({}))
    
    return render_template(
        "nlp/home.html",
        d=d,
    )

# === DATA IMPORT ===
@bp.route("/load_data", methods=["GET", "POST"])
#@protect_access
def load_data():

    # If d doesn't exist yet, create empty data with default (negative) data states
    # --> d <-- is the key variable in which we store our data throughhout the entire process of cleaning and analysis
    d = session.get("d", Data({}))

    # Initializing forms
    data_selection_form = DataSelection()
    example_data_form = ExampleData()

    #### (METHOD 1) DOWNLOAD DATA FROM LIMESURVEY
    if data_selection_form.submit.data and data_selection_form.validate():
        
        # Loading new data clears previosly stored data
        # with the exception of login information, csrf_token and storage
        # consider adding dataset information to the storage view
        clear_cached_data()

        data = imp.download_data_from_ls(
            data_selection_form.input_survey_number.data,
            data_selection_form.input_survey_column.data,
            data_selection_form.input_id_column.data,
        ) # and here we will add the ID column at some point

        d = Data(data)
        
        if errors_in_data(d):
            d.errors = True
        
        d.select() # select indicates that this is the currently active dataset
        d.set_source("lime")

    ### (METHOD 2) DOWNLOAD DATA FROM FILE
    # Uploading files in Flask: https://flask.palletsprojects.com/en/2.3.x/patterns/fileuploads/ 
    if "upload_form_file" in request.files:
        clear_cached_data()

        data = imp.load_data_from_file()
        d = Data(data)
        d.select()
        d.set_source("file")
            
    ### (METHOD 3) LOAD EXAMPLE DATA
    if example_data_form.submit_example.data and example_data_form.validate():

        clear_cached_data()

        data = imp.load_example_data()

        d = Data(data)
        d.select()
        d.set_source("example")
    
    # Saving the d object to cache
    session["d"] = d

    return render_template(
        "nlp/load_and_preprocess/load.html",
        d=d,
        data_selection_form=data_selection_form,
        example_data_form=example_data_form,
        storage=initiate_storage(),
    )

# DATA PREPROCESSING
@bp.route("/preprocess", methods=["GET", "POST"])
#@protect_access
def preprocess():

    # Load data from session and tokenize and clean it
    d = session.get("d", redirect("load_data")) # if d is not in session, redirect to load_data
    d.tokenize_and_clean()

    # Initializing forms
    stopwords_form = StopwordsForm()
    replacements_form = ReplacementsForm()

    if stopwords_form.validate_on_submit() and stopwords_form.submit_stopwords.data:
        d.add_remove_stopwords(
            stopwords_form.add_stopwords.data, 
            stopwords_form.remove_stopwords.data
        )
        d.tokenize_and_clean()

    if replacements_form.validate_on_submit() and replacements_form.submit.data:
        d.replace_tokens(replacements_form.replacements.data)
        d.tokenize_and_clean()

    return render_template(
        "nlp/load_and_preprocess/preprocess.html", 
        d=d,
        stopwords_form=stopwords_form,
        replacements_form=replacements_form,
        storage=initiate_storage(),
    )

# DATA EXPLORATION
@bp.route("/explore", methods = ["GET", "POST"])
#@protect_access
def explore():
    return redirect(url_for("nlp.explore_ngrams"))

@bp.route("/explore_ngrams", methods = ["GET", "POST"])
#@protect_access
def explore_ngrams():
    
    d = session.get("d")

    # Initializing forms
    ngrams_form = NgramsForm()
    
    # NGRAMS
    # Generating data for Ngrams
    top_words = d.generate_top_tokens("words")
    top_bigrams = d.generate_top_tokens("bigrams")
    top_trigrams = d.generate_top_tokens("trigrams")

    return render_template(
        "nlp/explore/explore_ngrams.html",
        d=d,
        top_words=top_words,
        top_bigrams=top_bigrams,
        top_trigrams=top_trigrams,
        ngrams_form=ngrams_form,
        storage=initiate_storage()
    )

@bp.route("/explore_network", methods = ["GET", "POST"])
#@protect_access
def explore_network():
    
    d = session.get("d")

    # Initializing forms
    network_form = NetworkForm()
    selected_words_form = SelectedWordsForm()

    # NETWORK VIZ
    if network_form.validate_on_submit():
        df = d.return_pandas_df()
        network_data = net.prepare_network_data(df)
        net.visualize_network(network_data, network_form.network_size.data)

    if selected_words_form.validate_on_submit() and selected_words_form.submit_words.data:
        df = d.return_pandas_df()
        selected_words_network_data = net.prepare_network_data(df)
        net.visualize_network_for_selected_words(selected_words_network_data, selected_words_form.choose_words.data)

    return render_template(
        "nlp/explore/explore_network.html",
        d=d,
        network_form=network_form,
        selected_words_form=selected_words_form,
        storage=initiate_storage(),
    )

# DATA MODELING

@bp.route("/model", methods = ["GET", "POST"])
#@protect_access
def model():
    return redirect(url_for("select_model"))

@bp.route("/select_model", methods = ["GET", "POST"])
#@protect_access
def select_model():

    d = session.get("d")

    # Initializing form
    model_selection_form = ModelSelection()
    
    if model_selection_form.validate_on_submit():
        return redirect(f"model/{model_selection_form.select_model.data}")

    return render_template(
        "nlp/model/select_model.html",
        d=d,
        model_selection_form=model_selection_form,
        storage=initiate_storage()
    )

# DATA MODELING
@bp.route("/model/word2vec", methods = ["GET", "POST"])
#@protect_access
def model_w2v():

    d = session.get("d")

    storage = initiate_storage()
    
    # Initializing forms
    modeling_form = ModelingForm()
    download_results_form = DownloadResults()

    if request.method == "POST":
        word2vec = load_w2v_gensim_model()

    w2v = None
    most_representative_terms = None
    display_summary=False
    
    if modeling_form.validate_on_submit():

        if modeling_form.pca_radio.data == "yes":
            w2v = W2V("word2vec + PCA", d.data)
            w2v.vectorize_documents(word2vec)
            w2v.n_clusters = modeling_form.n_of_ks_int.data # add setters instead
            w2v.pca_n_of_pcs = modeling_form.n_of_pcs_int.data
            w2v.perform_pca(modeling_form.standardize_pcs) # This replaces w2v vector representations of docs inside the w2v object into pcs!
            w2v.perform_mbkmeans()
            
            display_summary = True
            session["model"] = w2v # is it necessary to store the model in session if it is also stored in storage?
            
            storage.save_model(w2v)
            session["storage"] = storage

        if modeling_form.pca_radio.data == "no":
            w2v = W2V("word2vec", d.data)
            w2v.vectorize_documents(word2vec)
            w2v.n_clusters = modeling_form.n_of_ks_int.data
            w2v.perform_mbkmeans()
            most_representative_terms = w2v.generate_most_representative_terms(word2vec) # has to be create here to avoid passing the entire w2v model to template
            
            display_summary = True
            session["model"] = w2v # see above: is it necessary?

            storage.save_model(w2v)
            session["storage"] = storage

    return render_template(
        "nlp/model/model_w2v.html",
        d=d,
        w2v=w2v,
        most_representative_terms=most_representative_terms,
        display_summary=display_summary,
        modeling_form=modeling_form,
        silhouette_values=session.get("silhouette_values", None),
        cluster_summary=session.get("cluster_summary", None),
        download_results_form=download_results_form,
        storage=storage,
    )

@bp.route("/model/lda", methods = ["GET", "POST"])
#@protect_access
def model_lda():

    # Loading data
    d = session.get("d")

    # Initiating storage
    storage = initiate_storage()

    lda = LDA("LDA", d.data) # initializing lda

    # Initiating forms
    lda_coherence_form = LDACoherence(no_below=lda.no_below, no_above=lda.no_above)
    lda_model_form = LDAModel()

    # SCENARIO 1
    # Calculate coherence scores which are then passed to chart.js inside a template
    # Having no coherence scores will generate an error in template
    # Currently compare_coherence also triggers self.create_corpus
    # If the user enters the page with a get request
    # compare_coherence runs with default values.
    # By default the comparison is performed with low (below recommended) number of iterations
    if request.method == "GET":
        lda.compare_coherence(2,40,4)

    # SCENARIO 2
    # POST request with user-supplied parameters for the coherence form
    if lda_coherence_form.validate():
        lda.no_below=int(lda_coherence_form.no_below.data)
        lda.no_above=float(lda_coherence_form.no_above.data)
        
        lda.compare_coherence(
            lda_coherence_form.start.data,
            lda_coherence_form.end.data,
            lda_coherence_form.step.data,
            )
        
        session["lda"] = lda
    
    # SCENARIO 3
    # POST request with user-supplied parameters for the model form
    lda_summary_html = None
    lda_most_representative_words = None
    if lda_model_form.validate():

        lda.create_nltk_dict()
        lda.create_corpus()

        # Updata properties of the lda object with data from the form
        lda.no_below=int(lda_model_form.no_below.data)
        lda.no_above=float(lda_model_form.no_above.data)
        lda.n_iterations=lda_model_form.n_iterations.data
        lda.n_clusters=lda_model_form.n_clusters.data

        # Update model based on the new data

        lda.create_model()
        lda_most_representative_words = lda.generate_most_representative_words()
        lda_most_representative_words = lda_most_representative_words.to_html(index=False)
        
        lda_summary = lda.generate_summary()
        lda_summary_html = lda_summary.to_html(index=False)

        # Save model in storage
        storage.save_model(lda)
        session["storage"] = storage

    return render_template(
        "nlp/model/model_lda.html", 
        d=d,
        model=lda, # might not be necessary
        lda_coherence_form=lda_coherence_form,
        lda_model_form=lda_model_form,
        lda_summary_html=lda_summary_html,
        lda_most_representative_words=lda_most_representative_words,
        storage=storage,
    )

@bp.route("/model/nnmf", methods = ["GET", "POST"])
#@protect_access
def model_nnmf():

    # Loading data
    d = session.get("d")

    # Initiating storage
    storage = initiate_storage()

    nnmf = NNMF("NNMF", d.data) # initializing nnmf

    # Initiating forms
    nnmf_coherence_form = NNMFCoherence(no_below=nnmf.no_below, no_above=nnmf.no_above)
    nnmf_model_form = NNMFModel() # so far it's identical as lda
    # mabye drop nnmf/lda suffixes to simplify the code?

    # Scenario 1
    # Compare coherence for a set of predefined parameters for get requests 
    if request.method == "GET":
        nnmf.compare_coherence(2,40,4)

    # Scenario 2
    # TODO this should be moved to a function once I make sure that
    # there are no meaningful differences between LDA and NNMF.
    # POST request with user-supplied parameters for the coherence form
    if nnmf_coherence_form.validate():
        nnmf.no_below=int(nnmf_coherence_form.no_below.data)
        nnmf.no_above=float(nnmf_coherence_form.no_above.data)

        nnmf.compare_coherence(
            nnmf_coherence_form.start.data,
            nnmf_coherence_form.end.data,
            nnmf_coherence_form.step.data,
        )

        session["nnmf"] = nnmf
    
    # Scenario 3 
    # Just like above -- this probably should be moved to a function
    # POST request with user-supplied parameters for the model form
    nnmf_summary_html = None
    nnmf_most_representative_words = None
    if nnmf_model_form.validate():

        nnmf.create_nltk_dict()
        nnmf.create_corpus()

        # Update properties of the nnmf object with data from the form
        nnmf.no_below=int(nnmf_model_form.no_below.data)
        nnmf.no_above=float(nnmf_model_form.no_above.data)
        nnmf.n_iterations=nnmf_model_form.n_iterations.data
        nnmf.n_clusters=nnmf_model_form.n_clusters.data

        # Update model based on teh new data

        nnmf.create_model()
        nnmf_most_representative_words=nnmf.generate_most_representative_words()
        nnmf_most_representative_words=nnmf_most_representative_words.to_html(index=False)

        nnmf_summary = nnmf.generate_summary()
        nnmf_summary_html = nnmf_summary.to_html(index=False)

        # Save model 
        storage.save_model(nnmf)
        session["storage"] = storage

    return render_template(
        "nlp/model/model_nnmf.html", 
        d=d, 
        model=nnmf,
        nnmf_coherence_form=nnmf_coherence_form,
        nnmf_model_form=nnmf_model_form,
        nnmf_summary_html=nnmf_summary_html,
        nnmf_most_representative_words=nnmf_most_representative_words,
        storage=storage,
    )

@bp.route("/storage", methods = ["GET", "POST"])
#@protect_access
def show_storage():

    d = session.get("d")
    storage = initiate_storage()
    
    if request.method == "GET":
        models_numbered = storage.get_models_numbered()

    if request.method == "POST":
        for key in request.form:
            # Deleting models from storage
            if key.startswith('delete_'):
                model_number = int(key.split('_')[1])

                storage.delete_model(model_number)

            # Exporting models in storage to Excel 
            if key.startswith('download_'):
                model_number = int(key.split('_')[1])

                model_to_download = storage.models[model_number]

                if "word2vec" in model_to_download.model_type:
                    word2vec = load_w2v_gensim_model()
                    return model_to_download.write_to_excel(word2vec)

                return model_to_download.write_to_excel()
                
        models_numbered = storage.get_models_numbered()

    return render_template(
        "nlp/storage.html", 
        d=d, 
        models_numbered=models_numbered, 
        storage=storage,
    )