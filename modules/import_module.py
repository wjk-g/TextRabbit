import pandas as pd
from flask import request, session
from werkzeug.utils import secure_filename
import citric
from io import StringIO
import os

# Add: data_column:
# Add: id_column
def download_data_from_ls(survey_number, data_column, id_column=None):
    """
    Download LimeSurvey data in a base64 format
    - convert it to a pandas df
    - leave only two columns (id ("id") and respondents' answers ("text"))
    
    Args:
        survey_number: LimeSurvey survey number
        data_column: The name of the column containing text data
        id_column: The name of the id column
    """
    
    url = os.getenv('LIME_URL')
    username = os.getenv('LIME_USERNAME')
    password = os.getenv('LIME_PASSWORD')

    # We use the citric library to communicate with LimeSurvey API
    with citric.Client(url, username, password) as client:
            # exporting responses with Citric
            try:
                data = client.export_responses(survey_number, file_format="csv", \
                    completion_status="complete", response_type="long", \
                        heading_type="code" ) # importing only complete answers
            except citric.exceptions.LimeSurveyStatusError:
                return "survey_error"
            
            # decoding data    
            decoded_data = data.decode()
            string_data = StringIO(decoded_data)
            # transforming into pandas df
            df = pd.read_csv(string_data, sep=';')

            # If the user did not provide an id column,
            # the default id column is used.
            if not id_column:
                try:
                    df = df[["id", data_column]]
                    print("not id_column")
                except KeyError:
                    return "column_error"
            
            # If user provided the id column it will be used instead of the
            # default LimeSurvey "id" column.
            if id_column:
                try:
                    df = df[[id_column, data_column]]
                    print(df)
                    print(id_column)
                except KeyError:
                    return "column_error"
            
            

            df = df.dropna()
            df.columns = ["id", "text"] # setting new colnames

            return df

# TODO
# add id_column and data_column
def prep_loaded_data(df, data_column, id_column=None):
            df.reset_index(inplace=True)

            if not id_column:
                try:
                    df = df[["index", data_column]]
                    df.columns = ["id", "text"]
                except KeyError:
                    return "column_error"
            
            if id_column:
                try:
                    df = df[["index", id_column, data_column]]
                    df.drop(columns=["index"], inplace=True)
                    df.columns = ["id", "text"]
                except KeyError:
                    return "column_error"

            df.fillna("", inplace=True)
            df_dict = df.to_dict()
            return df_dict
            
# TODO
# Also add id_column
def load_data_from_file(app):

    ALLOWED_EXTENSIONS = {'txt', 'xlsx', 'xls', 'csv'}
    file = request.files['upload_form_file']
    filename = secure_filename(file.filename)
    extension = filename.rsplit('.', 1)[1].lower()

    if extension in ALLOWED_EXTENSIONS:
        file_path = os.path.join(app.root_path, 'uploads', filename)
        file.save(file_path)
        column = request.form.get("file_column")
        id = request.form.get("id_column", None)
        # This should work: id_column = request.form.get("id_column")
        # Add "id_column" field in load.html
    else:
        return "extension_error"

    if extension in ['xls', 'xlsx']:
        df = pd.read_excel('uploads/' + filename)
        return prep_loaded_data(df, column, id)
    elif extension in ['csv', 'txt']:
        df = pd.read_csv('uploads/' + filename)
        return prep_loaded_data(df, column, id)
    else:
        pass

# TODO
# Example data may also need extra column
def load_example_data():
    df = pd.read_csv("static/example_data.csv")
    df = df.dropna()
    print(df)
    df = df.to_dict()
    print(df)
    return df
    