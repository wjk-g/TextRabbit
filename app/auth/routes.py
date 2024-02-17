import os
import requests
import json

from oauthlib.oauth2 import WebApplicationClient
from dotenv import load_dotenv
from functools import wraps

# Flask imports
from flask import Flask, render_template, session, redirect, url_for, request

import sqlalchemy as sa
from app import db
from app.auth import bp

from app.models import User


# Detailed information on implementing Google Oauth in Flask
# can be found here: https://realpython.com/flask-google-login/

# OAuth CONFIGURATION

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", None) # Oauth
print(GOOGLE_CLIENT_ID)
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", None) # Oauth
GOOGLE_DISCOVERY_URL = ("https://accounts.google.com/.well-known/openid-configuration") # Oauth
client = WebApplicationClient(GOOGLE_CLIENT_ID) # Oauth
print(client)

@bp.route("/")
def index():
    # do not redirect if already authenticated
    return redirect("login")

def get_google_provider_cfg():
    # Tip: To make this more robust, you should add error handling to the Google API call, 
    # just in case Google’s API returns a failure and not the valid provider configuration document.
    return requests.get(GOOGLE_DISCOVERY_URL).json()

@bp.route("/login")
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

@bp.route("/login/callback")
def callback():
    # Get authorization code Google sent back to you
    code = request.args.get("code")
    # Find out what URL to hit to get tokens that allow you to ask for
    # things on behalf of a user
    google_provider_cfg = get_google_provider_cfg()
    token_endpoint = google_provider_cfg["token_endpoint"]

    # Prepare and send a request to get tokens
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
    
    # Decoding and extracting user information
    user_info_byte = userinfo_response.content
    user_info_decoded = user_info_byte.decode('utf-8')
    user_info = json.loads(user_info_decoded)
    user_email = user_info['email']
    
    user = User.query.filter_by(email=user_email).first()
    
    if user is None:
        new_user = User(email=user_email)
        db.session.add(new_user)
        db.session.commit()
        print(f"User {user_email} added to the database")
    else:
        print(f"User {user_email} already exists in the database!")

    return redirect(url_for("nlp.home"))

# === UTILITY FUNCTIONS ===
def protect_access(f):
    @wraps(f)
    def decorated_func(*args, **kwargs):
        if session.get("logged_in"):
            return f(*args, **kwargs)
        else:
            return redirect(url_for("auth.login"))
    return decorated_func
