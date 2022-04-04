import uuid

from flask import Flask, url_for, request, render_template, redirect, send_from_directory, g
import requests
from flask_wtf import FlaskForm
from flask_wtf.file import FileRequired, FileAllowed, FileField
from werkzeug.utils import secure_filename
from wtforms import StringField, PasswordField, BooleanField, SubmitField, EmailField, IntegerField
from wtforms.validators import DataRequired, Email, NumberRange
# noinspection PyUnresolvedReferences
from data.users import User
# noinspection PyUnresolvedReferences
from data import db_session
import os
from paginate_sqlalchemy import SqlalchemyOrmPage
from flask_login import login_user, LoginManager, current_user, logout_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'not-strong-key2'
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).filter(User.id == user_id).first()


@app.before_request
def before_request():
    g.user = current_user


class RegForm(FlaskForm):
    name = StringField('Имя', validators=[DataRequired()])
    surname = StringField('Фамилия', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    spam = BooleanField('Получать спам')
    age = IntegerField('Возраст', validators=[NumberRange(min=14, max=130)])
    job = StringField('Работа', validators=[DataRequired()])
    photo = FileField('Фото', validators=[FileAllowed(['jpg', 'png'], 'Images only!')])
    submit = SubmitField('Зарегистрироваться')


class LoginForm(FlaskForm):
    email = StringField('Имя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')


class UserEditForm(FlaskForm):
    name = StringField('Имя', validators=[DataRequired()])
    surname = StringField('Фамилия', validators=[DataRequired()])
    password = PasswordField('Новый пароль')
    email = EmailField('Email', validators=[DataRequired(), Email()])
    spam = BooleanField('Получать спам')
    admin = BooleanField('Админ')
    age = IntegerField('Возраст', validators=[NumberRange(min=14, max=130)])
    job = StringField('Работа', validators=[DataRequired()])
    photo = FileField('Обновить фото', validators=[FileAllowed(['jpg', 'png'], 'Images only!')])
    remove = SubmitField('Удалить аккаунт')
    submit = SubmitField('Сохранить изменения')


class UserViewForm(FlaskForm):
    name = StringField('Имя', render_kw={'disabled':''})
    surname = StringField('Фамилия', render_kw={'disabled':''})
    email = EmailField('Email', render_kw={'disabled':''})
    age = IntegerField('Возраст', render_kw={'disabled':''})
    job = StringField('Работа', render_kw={'disabled':''})


@app.route('/assets/<path:path>')
def send_report(path):
    return send_from_directory('assets', path)


@app.route('/login/', methods=['GET', 'POST'])
def login():
    if g.user is not None and g.user.is_authenticated:
        return redirect('/success/')
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        if not user:
            form.email.errors.append('Пользователь с такой почтой не найден')
            return render_template('login.html', title='Вход в систему', form=form)
        if not user.check_password(form.password.data):
            form.password.errors.append('Не угадали пароль')
            return render_template('login.html', title='Вход в систему', form=form)
        login_user(user)
        return redirect('/users/')
    return render_template('login.html', title='Вход в систему', form=form)


@app.route('/logout/', methods=['GET'])
def logout():
    logout_user()
    return redirect("/login/")


@app.route('/register/', methods=['GET', 'POST'])
def register():
    form = RegForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.email == form.email.data).first():
            form.email.errors.append('Пользователь с такой почтой уже зарегистрирован')
            return render_template('reg.html', title='Регистрация', form=form)
        user = User()
        user.name = form.name.data
        user.surname = form.surname.data
        user.set_password(form.password.data)
        user.email = form.email.data
        user.allow_spam = form.spam.data
        user.age = form.age.data
        user.job = form.job.data
        user.photo_link = "default.png"
        if form.photo.data:
            assets_dir = os.path.join(
                os.path.dirname(app.instance_path), 'assets'
            )
            image = form.photo.data
            user.photo_link = str(uuid.uuid4()) + '-' + secure_filename(image.filename)
            image.save(os.path.join(assets_dir, 'photos', user.photo_link))
        db_sess.add(user)
        db_sess.commit()
        return redirect('/success/')
    return render_template('reg.html', title='Регистрация', form=form)


@app.route('/users/')
def users_list():
    if g.user is not None and g.user.is_authenticated:
        db_sess = db_session.create_session()
        page = request.args.get('page')
        if page:
            page = int(page)
        else:
            page = 1
        result = SqlalchemyOrmPage(db_sess.query(User), page=page, items_per_page=2)
        return render_template('users.html', title='Пользователи', users=result, num=result.page_count,
                               cur_page=int(page), user=g.user)
    else:
        return redirect("/login")


@app.route('/profile/<path:id>', methods=['GET', 'POST'])
def user_edit(id):
    if g.user is not None and g.user.is_authenticated:
        if g.user.role == 1:
            admin = True
        else:
            admin = False
        if admin or int(id) == g.user.id:
            db_sess = db_session.create_session()
            user = db_sess.query(User).filter(User.id == id).first()
            if not user:
                return 'Пользователь не найден!', 404
            form = UserEditForm()
            if form.validate_on_submit() and (admin or id == g.user.id):
                if form.remove.data:
                    db_sess.delete(user)
                    db_sess.commit()
                    return redirect('/users/')
                user.name = form.name.data
                user.surname = form.surname.data
                if form.password.data:
                    user.set_password(form.password.data)
                user.email = form.email.data
                user.allow_spam = form.spam.data
                user.age = form.age.data
                user.job = form.job.data
                print(form.admin.data)
                if admin:
                    user.role = form.admin.data
                if form.photo.data:
                    assets_dir = os.path.join(
                        os.path.dirname(app.instance_path), 'assets'
                    )
                    image = form.photo.data
                    user.photo_link = str(uuid.uuid4()) + '-' + secure_filename(image.filename)
                    image.save(os.path.join(assets_dir, 'photos', user.photo_link))
                db_sess.merge(user)
                db_sess.commit()
                return redirect('/users/')
            if user.role > 0:
                form.admin.data = True
            form.name.data = user.name
            form.surname.data = user.surname
            form.email.data = user.email
            form.spam.data = user.allow_spam
            form.age.data = user.age
            form.job.data = user.job
            return render_template('edit.html', title='Редактирование профиля', form=form, admin=admin)
        else:
            db_sess = db_session.create_session()
            user = db_sess.query(User).filter(User.id == id).first()
            if not user:
                return 'Пользователь не найден!', 404
            form = UserViewForm()
            form.name.data = user.name
            form.surname.data = user.surname
            form.email.data = user.email
            form.age.data = user.age
            form.job.data = user.job
            return render_template('user.html', title='Просмотр профиля', form=form)
    else:
        return redirect("/login")


@app.route('/city_map/')
@app.route('/city_map/<city>')
def map2(city="Ульяновск"):
    path = f"static/map-not-found.png"
    fo = ""
    country = ""
    area = ""
    host = 'http://geocode-maps.yandex.ru/1.x/'
    if request.args.get('city'):
        city = request.args.get('city')
    params_query = {
        'apikey': 'bb8b1844-8ffd-4ac4-ab12-e879e77f924d',
        'geocode': city,
        'format': 'json',
    }
    resp = requests.get(host, params=params_query)
    if resp.status_code == 200:
        resp = resp.json()
        if int(resp["response"]["GeoObjectCollection"]["metaDataProperty"]["GeocoderResponseMetaData"]["found"]) > 0:
            data = resp["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]
            host = 'https://static-maps.yandex.ru/1.x/'
            params_query = {
                'll': str(data["Point"]["pos"]).replace(' ', ','),
                'spn': '0.016457,0.00619',
                'l': 'map',
            }
            resp = requests.get(host, params=params_query)
            if resp.status_code == 200:
                path = f"static/maps/map-{city}.png"
                fo = data["metaDataProperty"]["GeocoderMetaData"]["Address"]["Components"][1]["name"]
                country = data["metaDataProperty"]["GeocoderMetaData"]["Address"]["Components"][0]["name"]
                area = data["metaDataProperty"]["GeocoderMetaData"]["Address"]["Components"][2]["name"]
                with open(path, mode='wb') as f:
                    f.write(resp.content)
    else:
        return 'Internal error!', 500
    return render_template('map.html', city=city, path=path, fo=fo, country=country, area=area)


def main():
    db_session.global_init("db/users.db")

    # user = User()
    # user.name = "Пользователь 1"
    # user.about = "биография пользователя 1"
    # user.email = "email9999@email.ru"
    # db_sess.add(user)
    app.run(host='127.0.0.1', port=8080)


if __name__ == '__main__':
    main()
