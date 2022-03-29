from functools import wraps
from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators, SubmitField
from passlib.hash import sha256_crypt


# User Login Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("To view the this page please login!", "danger")
            return redirect(url_for("login"))

    return decorated_function


# User Login Check Decorator
def login_check(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            flash("You are already logged into your account!", "danger")
            return redirect(url_for("index"))
        else:
            return f(*args, **kwargs)

    return decorated_function


# User Register Form

class RegisterForm(Form):
    name = StringField("Name and Surname", validators=[validators.length(min=4, max=30)])

    username = StringField("Username", validators=[validators.length(min=5, max=35)])

    email = StringField("E-mail", validators=[validators.Email(message="Please enter a valid email address.")])

    password = PasswordField("Password", validators=[validators.DataRequired(message="Please set up a password."),
                                                     validators.EqualTo(fieldname="confirm",
                                                                        message="Your password doesn't match!")
                                                     ])
    confirm = PasswordField("Verify The Password")


# Login Form
class LoginFrom(Form):
    username = StringField("Username")
    password = PasswordField("Password")


# Posts Form
class PostsForm(Form):
    title = StringField("Title", validators=[validators.Length(min=5, max=100)])
    content = TextAreaField("Content", validators=[validators.Length(min=100, max=50000)])


# Comment Form
class CommentForm(Form):
    content = TextAreaField("Content", validators=[validators.Length(min=1, max=1000)])


app = Flask(__name__)

app.secret_key = "julia"

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "erasmusblog"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


# Post Update
@app.route("/edit/<string:id>", methods=["GET", "POST"])
@login_required
def update_post(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()

        query = "SELECT * FROM posts WHERE id = %s and  author = %s"

        data = cursor.execute(query, (id, session["username"]))

        if data == 0:
            flash("There is not such a Post with this id or You have not right to  edit this post!", "danger")
            cursor.close()
            return redirect(url_for("index"))
        else:
            post = cursor.fetchone()

            form = PostsForm()

            form.title.data = post["title"]
            form.content.data = post["content"]
            cursor.close()
            return render_template("update.html", form=form)
    else:
        # Post Request
        form = PostsForm(request.form)
        new_title = form.title.data
        new_content = form.content.data

        query_update = "UPDATE posts SET title = %s, content = %s WHERE id = %s"

        cursor = mysql.connection.cursor()

        cursor.execute(query_update, (new_title, new_content, id))

        mysql.connection.commit()

        cursor.close()

        flash("Post has been successfully updated.", "success")
        return redirect(url_for("dashboard"))


@app.route("/posts")
def posts():
    cursor = mysql.connection.cursor()
    query = "SELECT * FROM posts"

    data = cursor.execute(query)

    if data > 0:
        posts_data = cursor.fetchall()
        cursor.close()
        return render_template("posts.html", posts=posts_data)
    else:
        cursor.close()
        return render_template("posts.html")


@app.route("/posts/<string:name>/<string:id>")
def detail(name, id):
    return "Post Name: {}, Post id: {}".format(name, id)


@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    query = "SELECT * FROM posts WHERE author = %s"

    result = cursor.execute(query, (session["username"],))

    if result > 0:
        posts = cursor.fetchall()
        cursor.close()
        return render_template("dashboard.html", posts=posts)
    else:
        cursor.close()
        return render_template("dashboard.html")


# Register route
@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm(request.form)
    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)

        cursor = mysql.connection.cursor()

        query = "INSERT INTO users(name,email,username,password) VALUES (%s, %s, %s, %s)"

        cursor.execute(query, (name, email, username, password))

        mysql.connection.commit()

        cursor.close()

        flash(message="You have successfully registered.", category="success")

        return redirect(url_for("login"))
    else:
        return render_template("register.html", form=form)


# Login Process
@app.route("/login", methods=["GET", "POST"])
@login_check
def login():
    form = LoginFrom(request.form)
    if request.method == "POST":
        username = form.username.data
        password = form.password.data

        cursor = mysql.connection.cursor()

        query = "SELECT * FROM users WHERE username = %s"

        result = cursor.execute(query, (username,))

        if result > 0:
            data = cursor.fetchone()
            real_password = data["password"]
            if sha256_crypt.verify(password, real_password):
                flash("You have successfully logged in.", "success")

                session["logged_in"] = True
                session["username"] = username

                return redirect(url_for("index"))
            else:
                flash("Password is incorrect! Please Try Again.", "danger")
                return redirect(url_for("login"))
        else:
            flash("No User Found With This Username!", "danger")
            redirect(url_for("login"))

    return render_template("login.html", form=form)


# Delete Process
@app.route("/delete/<string:id>")
@login_required
def delete_post(id):
    cursor = mysql.connection.cursor()

    query = "SELECT * FROM posts WHERE author = %s and id = %s"

    data = cursor.execute(query, (session["username"], id))

    if data > 0:
        query2 = "DELETE FROM posts WHERE id = %s"
        cursor.execute(query2, (id,))
        mysql.connection.commit()
        cursor.close()
        flash("The post has been successfully deleted it.", "success")
        return redirect(url_for("dashboard"))
    else:
        flash("There is not such a Post with this id or You have not right to delete this post!", "danger")
        return redirect(url_for("index"))


# Detail Page
@app.route("/posts/<string:id>")
def detail_post(id):
    cursor = mysql.connection.cursor()

    query = "SELECT * FROM posts WHERE id = %s"

    data = cursor.execute(query, (id,))

    if data > 0:
        post = cursor.fetchone()
        return render_template("post.html", post=post)
    else:
        return render_template("post.html")


# Logout Process
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# Adding Post
@app.route("/addposts", methods=["GET", "POST"])
@login_required
def addposts():
    form = PostsForm(request.form)
    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data

        cursor = mysql.connection.cursor()

        query = "INSERT INTO posts(title, author, content) VALUES (%s, %s, %s)"

        cursor.execute(query, (title, session["username"], content))

        mysql.connection.commit()

        cursor.close()

        flash("Post has been created successfully.", "success")

        return redirect(url_for("dashboard"))
    else:
        return render_template("addpost.html", form=form)



# Search Route
@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword")

        cursor = mysql.connection.cursor()

        query = "SELECT * FROM posts WHERE title like '%" + keyword + "%' "

        data = cursor.execute(query)

        if data == 0:
            flash("No post with the searching keyword!", "warning")
            return redirect(url_for("posts"))
        else:
            posts = cursor.fetchall()
            return render_template("posts.html", posts=posts)


if __name__ == "__main__":
    app.run(debug=True)
