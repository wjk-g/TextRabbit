import os
import requests
import json
import pickle

from oauthlib.oauth2 import WebApplicationClient
from dotenv import load_dotenv
from functools import wraps

# Flask imports
from flask import Flask, render_template, session, redirect, url_for, request
from flask_session import Session

# Load forms
from forms import (DataSelection, ExampleData, StopwordsForm, ReplacementsForm,
                   NgramsForm, NetworkForm, SelectedWordsForm, ModelingForm, 
                   DownloadResults, ModelSelection, LDACoherence, LDAModel)

# Load classes
from data import Data
from models import LDA, NNMF, LSI, W2V
from storage import Storage

# Load functions
from modules.support_module import clear_cached_data
import modules.import_module as imp
import modules.network_module as net
import modules.model_module as mdl

from modules.model_module import vectorize_kv, perform_pca, mbkmeans_clusters, display_most_representative_terms

# Detailed information on implementing Oauth in Flask
# can be found here:
# https://realpython.com/flask-google-login/
#from oauthlib.oauth2 import WebApplicationClient


app = Flask(__name__)

# APP CONFIGURATION
app.secret_key = os.urandom(24)
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

UPLOAD_FOLDER = "/uploads"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 10 * 1000 * 1000 # max file size = 10 MB

# OAuth CONFIGURATION

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", None)
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", None)
GOOGLE_DISCOVERY_URL = ("https://accounts.google.com/.well-known/openid-configuration")
client = WebApplicationClient(GOOGLE_CLIENT_ID)

@app.route("/")
def index():
    # do not redirect if already authenticated
    return redirect("login")

def get_google_provider_cfg():
    # Tip: To make this more robust, you should add error handling to the Google API call, 
    # just in case Google’s API returns a failure and not the valid provider configuration document.
    return requests.get(GOOGLE_DISCOVERY_URL).json()

@app.route("/login")
def login():
    # Find out what URL to hit for Google login
    google_provider_cfg = get_google_provider_cfg()
    print(google_provider_cfg)
    # The field from the provider configuration document you need is called authorization_endpoint. 
    # This will contain the URL you need to use to initiate the OAuth 2 flow with Google from your client application.
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    # Use library to construct the request for Google login and provide
    # scopes that let you retrieve user's profile from Google
    # We use our pre-configured client that we already gave our Google Client ID to.
    # Next, we provide the redirect we want Google to use. Finally, we ask Google for a number of OAuth 2 scopes.

    # We can think of each scope as a separate piece of user information. 
    # We’re asking for the user’s email and basic profile information from Google. 
    # The user will, of course, have to consent to give us this information.
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=request.base_url + "/callback",
        scope=["openid", "email", "profile"],
    )
    return redirect(request_uri)

@app.route("/login/callback")
def callback():
    print("Initiating callback view function")
    # Get authorization code Google sent back to you
    code = request.args.get("code")
    # Find out what URL to hit to get tokens that allow you to ask for
    # things on behalf of a user
    google_provider_cfg = get_google_provider_cfg()
    token_endpoint = google_provider_cfg["token_endpoint"]

    # Prepare and send a request to get tokens! Yay tokens!
    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
        code=code
        )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
        )
    
    # Parse the tokens!
    client.parse_request_body_response(json.dumps(token_response.json()))

    # Now that you have tokens (yay) let's find and hit the URL
    # from Google that gives you the user's profile information,
    # including their Google profile image and email
    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)

    userinfo_response = requests.get(uri, headers=headers, data=body)
    session["logged_in"] = True
    
    return redirect(url_for("load_data"))

# === UTILITY FUNCTIONS ===
def protect_access(f):
    @wraps(f)
    def decorated_func(*args, **kwargs):
        if session.get("logged_in"):
            return f(*args, **kwargs)
        else:
            return redirect("login")
    return decorated_func

# Initiate storage helper function
def initiate_storage():
    storage = session.get("storage")
    if not storage:
        storage = Storage()
        session["storage"] = storage
    return storage

def load_w2v_gensim_model():
    path_to_gensim_model = "static/word2vec/word2vec_gensim_nkjp_wiki_lemmas_all_300_cbow_hs.pickle"
    with open(path_to_gensim_model, 'rb') as gensim_model:
        word2vec = pickle.load(gensim_model)
    return word2vec

# === DATA IMPORT ===
@app.route("/load_data", methods=["GET", "POST"])
@protect_access
def load_data():
    print(session.get("logged_in"))

    # If d doesn't exist yet, create empty data with default (negative) data states
    # --> d <-- is the key variable in which we store our data throughhout the entire process of cleaning and analysis
    d = session.get("d", Data({}))

    # Initializing forms
    data_selection_form = DataSelection()
    example_data_form = ExampleData()

    ### (METHOD 1) DOWNLOAD DATA FROM LIMESURVEY
    if data_selection_form.submit.data and data_selection_form.validate():
        
        # Loading new data clears previosly stored data
        # with the exception of login information, csrf_token and storage
        # consider adding dataset information to the storage view
        clear_cached_data()

        data = imp.download_data_from_ls(data_selection_form.input_survey_number.data,
                                        data_selection_form.input_survey_column.data)
                                        # and here we will add the ID column at some point
        d = Data(data)
        d.select() # select indicates that this is the currently active dataset

    ### (METHOD 2) DOWNLOAD DATA FROM FILE
    # Uploading files in Flask: https://flask.palletsprojects.com/en/2.3.x/patterns/fileuploads/ 
    if "upload_form_file" in request.files:
        clear_cached_data()

        data = imp.load_data_from_file(app=app)
        d = Data(data)
        d.select()
            
    ### (METHOD 3) LOAD EXAMPLE DATA
    if example_data_form.submit_example.data and example_data_form.validate():

        clear_cached_data()

        data = imp.load_example_data() # gives me a dict
                                # will need fake id col
        d = Data(data)
        d.select()
        d.mark_as_example_data()
    
    # Saving the d object to cache
    session["d"] = d

    return render_template(
        "load.html",
        d=d,
        data_selection_form=data_selection_form,
        example_data_form=example_data_form,
        storage=initiate_storage(),
    )

# DATA PREPROCESSING
@app.route("/preprocess", methods=["GET", "POST"])
@protect_access
def preprocess():

    # Load data from session and tokenize and clean it
    d = session.get("d", redirect("load_data"))
    d.tokenize_and_clean()

    # Initializing forms
    stopwords_form = StopwordsForm()
    replacements_form = ReplacementsForm()

    if stopwords_form.validate_on_submit() and stopwords_form.submit_stopwords.data:
        d.add_remove_stopwords(stopwords_form.add_stopwords.data, 
                               stopwords_form.remove_stopwords.data)
        d.tokenize_and_clean()

    if replacements_form.validate_on_submit() and replacements_form.submit.data:
        d.replace_tokens(replacements_form.replacements.data)
        d.tokenize_and_clean()

    return render_template(
        "preprocess.html", 
        d=d,
        stopwords_form=stopwords_form,
        replacements_form=replacements_form,
        storage=initiate_storage(),
    )

# DATA EXPLORATION
@app.route("/explore", methods = ["GET", "POST"])
@protect_access
def explore():
    return redirect(url_for("explore_ngrams"))

@app.route("/explore_ngrams", methods = ["GET", "POST"])
@protect_access
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
        "explore_ngrams.html",
        d=d,
        top_words=top_words,
        top_bigrams=top_bigrams,
        top_trigrams=top_trigrams,
        ngrams_form=ngrams_form,
        storage=initiate_storage()
    )

@app.route("/explore_network", methods = ["GET", "POST"])
@protect_access
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
        "explore_network.html",
        d=d,
        network_form=network_form,
        selected_words_form=selected_words_form,
        storage=initiate_storage(),
    )

# DATA MODELING

#@protect_access
@app.route("/model", methods = ["GET", "POST"])
def model():
    return redirect(url_for("select_model"))

#@protect_access
@app.route("/select_model", methods = ["GET", "POST"])
def select_model():

    d = session.get("d")

    # Initializing form
    model_selection_form = ModelSelection()
    
    if model_selection_form.validate_on_submit():
        return redirect(f"model/{model_selection_form.select_model.data}")

    return render_template(
        "model/select_model.html",
        d=d,
        model_selection_form=model_selection_form,
        storage=initiate_storage()
    )

# DATA MODELING
#@protect_access
@app.route("/model/word2vec", methods = ["GET", "POST"])
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
            print(most_representative_terms)
            
            display_summary = True
            session["model"] = w2v # see above: is it necessary?

            storage.save_model(w2v)
            session["storage"] = storage

    #if download_results_form.validate_on_submit() and download_results_form.download_data_submit.data:
    #    if session.get("model"): # TODO downloading should be moved to a separate tab
    #        model = session.get("model", False)
    #        if model:
    #            return W2V.write_to_excel(word2vec, model)

    return render_template(
        "model/model_w2v.html",
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

#@protect_access
@app.route("/model/lda", methods = ["GET", "POST"])
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
    # If the user enters the page with a get request default values
    # compare_coherence runs with default values.
    # By default the comparison is performed with low (before recommended) number of iterations
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
            lda_coherence_form.step.data
            )
        
        session["lda"] = lda
    
    # SCENARIO 3
    # POST request with user-supplied parameters for the model form
    lda_summary_html = None
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
        
        lda_summary = lda.generate_summary()
        lda_summary_html = lda_summary.to_html()

        # Save model in storage
        storage.save_model(lda)
        session["storage"] = storage

    return render_template(
        "model/model_lda.html", 
        d=d, 
        model=lda, # might not be necessary
        lda_coherence_form=lda_coherence_form,
        lda_model_form=lda_model_form,
        lda_summary_html=lda_summary_html,
        storage=storage,
    )

#@protect_access
@app.route("/model/nnmf", methods = ["GET", "POST"])
def model_nnmf():

    # Form
        # no_below
        # no_above
        # n_of_ks
        # --no iterations

    d = session.get("d")
    storage = initiate_storage()

    nnmf = NNMF("NNMF", d.data) # initializing lda
    nnmf.compare_coherence(2,40,4) # initial comp performed at low iter (250)
    nnmf.create_model()

    return render_template("model/model_nnmf.html", d=d, model=nnmf, storage=storage)

#@protect_access
@app.route("/model/lsi", methods = ["GET", "POST"])
def model_lsi():

    # Form
        # no_below
        # no_above
        # n_of_ks
        # iterations

    d = session.get("d")
    storage = initiate_storage()

    lsi = LSI("LSI", d.data) # initializing lda
    lsi.compare_coherence(2,40,4) # initial comp performed at low iter (250)
    lsi.create_model()
    lsi.show_topics()

    return render_template("model/model_lsi.html", d=d, model=lsi, storage=storage)

@app.route("/storage", methods = ["GET", "POST"])
def show_storage():

    d = session.get("d")
    storage = initiate_storage()
    
    if request.method == "GET":
        
        table_of_models = storage.return_html_summary()

    if request.method == "POST":
        for key in request.form:
            # Deleting models from storage
            if key.startswith('delete_'):
                model_number = int(key.split('_')[1])

                storage.delete_model(model_number)

            # Exporting models in storage to Excel 
            if key.startswith('download_'):
                model_number = int(key.split('_')[1])
                # trigger model's download method

                model_to_download = storage.models[model_number]
                print(model_to_download)
                word2vec = load_w2v_gensim_model()

                return model_to_download.write_to_excel(word2vec)
                
        table_of_models = storage.return_html_summary()

    return render_template(
        "storage.html", 
        d=d, 
        table_of_models=table_of_models, 
        storage=storage,
    )

if __name__ == "__main__":
    app.run(debug=True, port=5050)#, ssl_context="adhoc")
