from flask_wtf import FlaskForm
from wtforms import (
    SelectField, 
    SubmitField,
)
from wtforms.validators import DataRequired, InputRequired
from flask_wtf.file import FileField, FileAllowed

class TranscribeForm(FlaskForm):
    select_language = SelectField('Wybierz język nagrania', choices=[
        ('pl', 'polski'), 
        ('en', 'angielski globalny'),
        ('en_uk', 'angielski brytyjski'),
        ('en_us', 'angielski amerykański'),
        ('uk', 'ukraiński'),
        ('ru', 'rosyjski'),
        ('auto', 'wykryj automatycznie')],
        validators=[DataRequired()]
        )
    file_upload = FileField(
        'Załaduj plik audio',
        validators=[
            FileAllowed(["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"], 'Tylko pliki audio!'),
            InputRequired(),
        ]
    )
    submit = SubmitField('Zleć transkrypcję')