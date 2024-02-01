import os
import requests
import json
import pickle
import pandas as pd

from oauthlib.oauth2 import WebApplicationClient
from dotenv import load_dotenv
from functools import wraps

# API's
# OpenAI
from openai import OpenAI
#from pydub import AudioSegment
import whisper
import time
# Google cloud
from google.cloud import speech_v1p1beta1 as speech
from google.cloud import storage
# AssemblyAI
import assemblyai as aai

from werkzeug.utils import secure_filename

# Flask imports
from flask import Flask, render_template, session, redirect, url_for, request, jsonify, send_file
from flask_session import Session

# Load forms
from forms import (
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
    TranscribeForm,
)

# Load classes
from data import Data
from models import LDA, NNMF, W2V #LSI
from storage import Storage
from transcripts import TranscriptsHandler
#from modules.audio_module import convert_to_mp3_and_split

# Load functions
from modules.support_module import clear_cached_data
import modules.import_module as imp
import modules.network_module as net
import modules.model_module as mdl

# Detailed information on implementing Oauth in Flask
# can be found here:
# https://realpython.com/flask-google-login/
# from oauthlib.oauth2 import WebApplicationClient


app = Flask(__name__)

# APP CONFIGURATION
app.secret_key = os.urandom(24)
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

UPLOAD_FOLDER = "/uploads"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 300 * 1000 * 1000 # max file size = 300 MB

# OAuth CONFIGURATION

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", None) # Oauth
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", None) # Oauth
GOOGLE_DISCOVERY_URL = ("https://accounts.google.com/.well-known/openid-configuration") # Oauth
client = WebApplicationClient(GOOGLE_CLIENT_ID) # Oauth

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
    
    return redirect(url_for("home"))

# === UTILITY FUNCTIONS ===
def protect_access(f):
    @wraps(f)
    def decorated_func(*args, **kwargs):
        if session.get("logged_in"):
            return f(*args, **kwargs)
        else:
            return redirect("login")
    return decorated_func

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
    path_to_gensim_model = "static/word2vec/word2vec_gensim_nkjp_wiki_lemmas_all_300_cbow_hs.pickle"
    with open(path_to_gensim_model, 'rb') as gensim_model:
        word2vec = pickle.load(gensim_model)
    return word2vec


# === HOME ===

@app.route("/home", methods=["GET", "POST"])
@protect_access
def home():
    d = session.get("d", Data({}))
    
    return render_template(
        "home.html",
        d=d,
    )

# === DATA IMPORT ===
@app.route("/load_data", methods=["GET", "POST"])
@protect_access
def load_data():

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

        data = imp.download_data_from_ls(
            data_selection_form.input_survey_number.data,
            data_selection_form.input_survey_column.data,
            data_selection_form.input_id_column.data,
        ) # and here we will add the ID column at some point

        d = Data(data)
        
        if errors_in_data(d):
            d.errors = True
        
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

        data = imp.load_example_data()

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
        d.add_remove_stopwords(
            stopwords_form.add_stopwords.data, 
            stopwords_form.remove_stopwords.data
        )
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

@app.route("/model", methods = ["GET", "POST"])
@protect_access
def model():
    return redirect(url_for("select_model"))

@app.route("/select_model", methods = ["GET", "POST"])
@protect_access
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
@app.route("/model/word2vec", methods = ["GET", "POST"])
@protect_access
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

@app.route("/model/lda", methods = ["GET", "POST"])
@protect_access
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
        "model/model_lda.html", 
        d=d,
        model=lda, # might not be necessary
        lda_coherence_form=lda_coherence_form,
        lda_model_form=lda_model_form,
        lda_summary_html=lda_summary_html,
        lda_most_representative_words=lda_most_representative_words,
        storage=storage,
    )

@app.route("/model/nnmf", methods = ["GET", "POST"])
@protect_access
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
        "model/model_nnmf.html", 
        d=d, 
        model=nnmf,
        nnmf_coherence_form=nnmf_coherence_form,
        nnmf_model_form=nnmf_model_form,
        nnmf_summary_html=nnmf_summary_html,
        nnmf_most_representative_words=nnmf_most_representative_words,
        storage=storage,
    )

#@app.route("/model/lsi", methods = ["GET", "POST"])
#@protect_access
#def model_lsi():
#
#    # Form
#        # no_below
#        # no_above
#        # n_of_ks
#        # iterations
#
#    d = session.get("d")
#    storage = initiate_storage()
#
#    lsi = LSI("LSI", d.data) # initializing lda
#    lsi.compare_coherence(2,40,4) # initial comp performed at low iter (250)
#    lsi.create_model()
#    lsi.show_topics()
#
#    return render_template("model/model_lsi.html", d=d, model=lsi, storage=storage)

@app.route("/storage", methods = ["GET", "POST"])
@protect_access
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
        "storage.html", 
        d=d, 
        models_numbered=models_numbered, 
        storage=storage,
    )

@app.route("/transcribe", methods = ["GET", "POST"])
@protect_access
def transcribe():
    
    d = session.get('d')
    transcribe_form = TranscribeForm()
    
    if request.method == "GET":
        return render_template(
            "transcribe.html", 
            d=d,
            storage=initiate_storage(),
            transcribe_form=transcribe_form,
            user_transcripts = session.get("user_transcripts", ""),
            request_method=request.method,
            form_valid=True,
        )

    if transcribe_form.validate_on_submit():

        form_valid = True
        transcription_submitted = False
        
        audio_file = request.files['file_upload']
        #print(audio_file)
        #TODO change the name of the folder
        #TODO automatically delete files after they're submitted for transcritption
        audio_file.save(f"./test_audio/{audio_file.filename}")
        
        if audio_file:
            aai.settings.api_key = os.getenv('ASSEMBLYAI_API_KEY')
            config = aai.TranscriptionConfig(
                language_code=transcribe_form.select_language.data,
                speaker_labels=True,
                punctuate=True, 
                format_text=True,
            )

            transcriber = aai.Transcriber()

            transcript = transcriber.submit(
                f"./test_audio/{audio_file.filename}",
                config=config,
            )

            transcript_id = transcript.id

            if session.get("transcripts_in_session_ids"):
                session["transcripts_in_session_ids"].append(transcript_id)
            else:
                session["transcripts_in_session_ids"] = [transcript_id]

            transcription_submitted = True
        
            return render_template(
                "transcribe.html", 
                d=d,
                storage=initiate_storage(),
                transcribe_form=transcribe_form,
                #user_transcripts = session.get("user_transcripts", ""),
                transcription_submitted=transcription_submitted,
                form_valid=form_valid,
                request_method=request.method,
            )
        
    if request.method == 'POST' and not transcribe_form.validate_on_submit():
        
        form_valid = False
        transcription_submitted = False

        return render_template(
                "transcribe.html", 
                d=d,
                storage=initiate_storage(),
                transcribe_form=transcribe_form,
                #user_transcripts = session.get("user_transcripts", ""),
                transcription_submitted=transcription_submitted,
                form_valid=form_valid,
                request_method=request.method,
            )

@app.route("/retrieve_transcripts", methods = ["GET", "POST"])
@protect_access
def retrieve_transcripts():
    
    d = session.get("d")

    transcripts_handler = TranscriptsHandler()

    api_key = os.getenv('ASSEMBLYAI_API_KEY')
    
    transcripts_in_session_ids = session.get("transcripts_in_session_ids")

    transcripts_in_session = []

    transcripts_being_processed = []
    session["transcripts_being_processed"] = transcripts_being_processed

    # TODO duplicated, put it in a function
    if transcripts_in_session_ids:
        transcripts_handler.get_response_from_api(api_key=api_key, limit=100)
        transcripts_handler.get_transcripts_in_session(transcripts_in_session_ids)
        
        # All transcripts in session
        transcripts_in_session = transcripts_handler.transcripts_in_session

        # All transcripts being processed
        transcripts_being_processed = [t["id"] for t in transcripts_in_session if t["status"] == "processing"]

        session["transcripts_being_processed"] = transcripts_being_processed
        # example: {"status": "processing", "id": 123}, {"status": "processing", "id": 456}

    if request.method == "POST":
        for key in request.form:
            if key.startswith('download_'):
                transcript_id = key.split('_')[1]
                return transcripts_handler.download_transcript(transcript_id)

    return render_template(
        "retrieve_transcripts.html", 
        d=d,
        storage=initiate_storage(),
        transcripts=transcripts_in_session,
        transcripts_being_processed=transcripts_being_processed,
        user_transcripts = session.get("transcripts_in_session_ids"),
    )


@app.route('/check_transcripts_status', methods=['GET'])
def check_transcripts_status():

    transcripts_handler = TranscriptsHandler()
    api_key = os.getenv('ASSEMBLYAI_API_KEY')
    transcripts_being_processed = session.get("transcripts_being_processed")

    transcripts_handler.get_response_from_api(api_key=api_key, limit=100)

    transcripts_statuses = [ transcripts_handler.get_transcript_status(t) for t in transcripts_being_processed ]

    if transcripts_statuses:
        completed = any(status != 'processing' for status in transcripts_statuses)
    else:
        completed = False

    return jsonify({"reload": completed}), 200

if __name__ == "__main__":
    app.run(debug=False, port=5050)#, ssl_context="adhoc")
