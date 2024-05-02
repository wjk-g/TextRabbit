from flask_wtf import FlaskForm
from wtforms import (
    TextAreaField,
    StringField,
    SubmitField
)

from wtforms.validators import DataRequired, InputRequired


class CreateProjectForm(FlaskForm):
    name = StringField('Nazwa projektu', validators=[DataRequired()])
    description = TextAreaField('Opis projektu', validators=[DataRequired()])
    submit = SubmitField('Utwórz projekt')

class ModifyProjectForm(CreateProjectForm):
    submit = SubmitField('Zapisz zmiany')