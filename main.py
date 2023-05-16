import sqlite3

from flask import Flask, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from forms import CreatePostForm, RegistrationForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from sqlalchemy.exc import IntegrityError
from functools import wraps


app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)
login_manager = LoginManager()
login_manager.init_app(app)


# CONNECT TO DB

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# CONFIGURE TABLES
# ⬇️Created three tables inside the blog (config in URI) database ⬇️
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    comment_on_blog = relationship("Comment", back_populates="post_to_comment")
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    author = relationship("User", back_populates="posts")
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(250), unique=True, nullable=False)
    name = db.Column(db.String(250), nullable=False)
    password = db.Column(db.String(250), nullable=False)
    posts = relationship("BlogPost", back_populates="author")
    comment = relationship("Comment", back_populates="comment_author")


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    comment_author = relationship("User", back_populates="comment")
    blog_post_id = db.Column(db.Integer, db.ForeignKey('blog_posts.id'))
    post_to_comment = relationship("BlogPost", back_populates="comment_on_blog")


with app.app_context():
    db.create_all()
    db.session.flush()
# ⬆ Created three tables inside the blog database ⬆️

# Initializing Gravatar for profil pics
gravatar = Gravatar(app, size=100, rating='g', default='retro',
                    force_default=False, force_lower=False, use_ssl=False, base_url=None)


# ⬇️Decorator that disables access to certain webpages ⬇️
def admin_only(original_func):
    @wraps(original_func)
    def wrapper(*args, **kwargs):
        if current_user.id is None or current_user.id != 1:
            original_func(*args, **kwargs)
            return redirect(url_for("forbidden"))
        else:
            return original_func(*args, **kwargs)

    return wrapper
# ⬆ Decorator that disables access to certain webpages ⬆️


@login_manager.user_loader
def load_user(user_id):
    return User.query.filter_by(id=user_id).first()


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    with app.app_context():
        db.session.flush()
    return render_template("index.html", all_posts=posts)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if request.method == 'POST':
        name = form.name.data
        password = form.password.data
        password = generate_password_hash(password, method='pbkdf2', salt_length=16)
        email = form.email.data
        try:
            with app.app_context():
                registered_user = User()
                registered_user.email = email
                registered_user.name = name
                registered_user.password = password
# ⬆ Another way to insert  would be registered_user = Users(name=name, email=email, password = password)... ⬆
                db.session.add(registered_user)
                db.session.commit()
            login_user(User.query.filter_by(email=email).first())
            return redirect(url_for('get_all_posts'))
        except IntegrityError:
            flash("You've already signed up with that email. Log In instead.")
            return redirect(url_for('login'))
    else:
        return render_template("register.html", form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if request.method == 'POST':
        # Note: form.data gets all the information associated with the form
        email = form.email.data
        password = form.password.data
        try:
            user_data = User.query.filter_by(email=email).first()
            if check_password_hash(user_data.password, password):
                login_user(user=user_data)
                return redirect(url_for('get_all_posts'))
            else:
                flash('Password incorrect. Please check.')
                return redirect(url_for("login"))
        except AttributeError:
            flash("The email does not exist. Please try again.")
    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    form = CommentForm()
    comments = Comment.query.filter_by(blog_post_id=post_id)
    if request.method == "POST":
        if current_user.is_anonymous:
            flash(message="Please log-in to comment.")
        else:
            comment = form.comment.data
            if form.validate_on_submit():
                with app.app_context():
                    this_post = db.session.merge(requested_post)
                    new_comment = Comment(
                        text=comment,
                        comment_author=current_user,
                        post_to_comment=this_post
                    )
                    db.session.add(new_comment)
                    db.session.commit()

    return render_template("post.html", post=requested_post, form=form, comments=comments)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact", methods=['POST', 'GET'])
def contact():
    return render_template("contact.html")


@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():

    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        # post.author = post.author.name
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/forbidden_403")
def forbidden():
    return render_template("403error.html")


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
