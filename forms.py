from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField, IntegerField, StringField, TextAreaField, RadioField, DecimalField
from wtforms.validators import DataRequired, InputRequired, NumberRange
#from flask_wtf.file import FileField, FileAllowed


# LOAD
class DataSelection(FlaskForm):
    input_survey_number = IntegerField("Wprowadź numer ankiety")
    input_survey_column = StringField("Wprowadź kod pytania z danymi tekstowymi")
    submit = SubmitField("Załaduj dane")

class ExampleData(FlaskForm):
    submit_example = SubmitField("Załaduj przykładowy zbiór danych")

# PREPROCESS
class StopwordsForm(FlaskForm):
    add_stopwords = TextAreaField("(+) Wprowadź słowa, które chcesz dodać do listy stopwords.")
    remove_stopwords = TextAreaField("(-) Wprowadź słowa, które chcesz usunąć z listy stopwords.")
    submit_stopwords = SubmitField("Dodaj/usuń stopwords")

class ReplacementsForm(FlaskForm):
    replacements = TextAreaField("Wprowadź tokeny, które chcesz zmienić.")
    submit = SubmitField("Zatwierdź zmiany")

# EXPLORE
class NgramsForm(FlaskForm):
    ngram = SelectField("Wybierz ngram",
                        choices = [("words", "Pojedyncze słowa"), ("bigrams", "Bigramy"), ("trigrams", "Trigramy")])
    #submit = SubmitField("Zatwierdź")

class NetworkForm(FlaskForm):
    network_size = IntegerField("Określ rozmiar sieci", validators=[InputRequired()])
    submit = SubmitField("Wygeneruj sieć")

class SelectedWordsForm(FlaskForm):
    choose_words = TextAreaField("Wprowadź słowa")
    submit_words = SubmitField("Wygeneruj sieć")

# MODEL
class ModelSelection(FlaskForm):
    select_model = SelectField("Wybierz model",
                        choices = [("word2vec", "word2vec"), 
                                   ("lda", "Latent Dirichlet Allocation"), 
                                   ("nnmf", "Non-Negative Matrix Factorization"),
                                   ("lsi", "Latent Semantic Indexing")])
    submit_select_model = SubmitField("Zatwierdź wybór")

class ModelingForm(FlaskForm):
    pca_radio = RadioField("Czy chcesz wykonać analizę głównych składowych przed analizą skupień?",
                            choices = [('yes', 'Tak'),
                                        ('no', 'Nie')], default='no', validators=[DataRequired()],
                            )
    n_of_pcs_int = IntegerField("Wybierz liczbę głównych składowych", default=2, validators=[NumberRange(min=2, max=100, message="sdgsdgs")])
    standardize_pcs = RadioField("Czy chcesz zestandaryzdować główne składowe?",
                                 choices = [('yes', 'Tak'), ('no', 'Nie')], default='no', validators=[DataRequired()])
    n_of_ks_int = IntegerField("Wybierz liczbę skupień", validators=[NumberRange(min=2, max=100, message="sdgsdgs")])
    submit_clustering = SubmitField("Zatwierdzam")

class DownloadResults(FlaskForm):
    download_data_submit = SubmitField("Pobierz")

# LDA 

class LDAModel(FlaskForm):
    no_below = IntegerField("Nie mniej razy niż:", 
                            validators=[NumberRange(min=0, max=500, 
                                                    message="Podaj liczbę całkowitę z przedziału od 0 do 500")])
    no_above = DecimalField("Częstość występowania nie większa niż:",
                          validators=[NumberRange(min=0.0, max=1.0,
                                                  message="Podaj wartość z przedziału od 0 do 1")])
    n_iterations = IntegerField("Liczba iteracji:", 
                                validators=[NumberRange(min=250, max=1000,
                                                        message="Podaj liczbę całkowitę z przedziału od 250 do 1000")])
    n_clusters = IntegerField("Liczba skupień:", 
                                validators=[NumberRange(min=2, max=500,
                                                        message="Podaj liczbę całkowitę z przedziału od 2 do 500")])
    submit = SubmitField("Zatwierdź")

class LDACoherence(FlaskForm):
    start = IntegerField("Start", validators=[NumberRange(min=1, max=500, # TODO has to be lower than end
                                                    message="Podaj liczbę całkowitę z przedziału od 1 do 500")])
    end = IntegerField("End", validators=[NumberRange(min=1, max=500,
                                                    message="Podaj liczbę całkowitę z przedziału od 1 do 500")])
    step = IntegerField("Step", validators=[NumberRange(min=1, max=5, 
                                                    message="Podaj liczbę całkowitę z przedziału od 1 do 5")])
    no_below = IntegerField("Nie mniej razy niż:", 
                            validators=[NumberRange(min=0, max=500, 
                                                    message="Podaj liczbę całkowitę z przedziału od 0 do 500")])
    no_above = DecimalField("Częstość występowania nie większa niż:", 
                          validators=[NumberRange(min=0.0, max=1.0,
                                                  message="Podaj wartość z przedziału od 0 do 1")])
    submit = SubmitField("Zatwierdź")
