import os
from flask import (
    Flask, flash, render_template,
    redirect, request, session, url_for)
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
if os.path.exists("env.py"):
    import env


app = Flask(__name__)

app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")

mongo = PyMongo(app)


@app.route("/")
@app.route("/home")
def home():
    return render_template("home.html")


@app.route("/get_jobs")
def get_jobs():
    jobs = list(mongo.db.jobs.find())
    return render_template("jobs.html", jobs=jobs)


@app.route("/search", methods=["GET", "POST"])
def search():
    query = request.form.get("query")
    jobs = list(mongo.db.jobs.find({"$text": {"$search": query}}))
    return render_template("jobs.html", jobs=jobs)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # check if username already exists in db
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        if existing_user:
            flash("Username already exists")
            return redirect(url_for("register"))

        register = {
            "username": request.form.get("username").lower(),
            "password": generate_password_hash(request.form.get("password"))
        }
        mongo.db.users.insert_one(register)

        # put the new user into 'session' cookie
        session["user"] = request.form.get("username").lower()
        flash("Registration Successful!")
        return redirect(url_for("profile", username=session["user"]))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # check if username exists in db
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        if existing_user:
            # ensure hashed password matches user input
            if check_password_hash(
                    existing_user["password"], request.form.get("password")):
                session["user"] = request.form.get("username").lower()
                flash("Welcome, {}".format(request.form.get("username")))
                return redirect(url_for("profile", username=session["user"]))
            else:
                # invalid password match
                flash("Incorrect Username and/or Password")
                return redirect(url_for("login"))

        else:
            # username doesn't exist
            flash("Incorrect Username and/or Password")
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/profile/<username>", methods=["GET", "POST"])
def profile(username):
    # grab the session user's username from db
    username = mongo.db.users.find_one(
        {"username": session["user"]})["username"]

    if session["user"]:
        return render_template("profile.html", username=username)

    return redirect(url_for("login"))


@app.route("/logout")
def logout():
    # remove user from session cookie
    flash("You have been logged out")
    session.pop("user")
    return redirect(url_for("login"))


@app.route("/request_job", methods=["GET", "POST"])
def request_job():
    if request.method == "POST":
        is_urgent = "on" if request.form.get("is_urgent") else "off"
        job = {
            "job_category": request.form.get("job_category"),
            "job_name": request.form.get("job_name"),
            "job_description": request.form.get("job_description"),
            "job_location": request.form.get("job_location"),
            "is_urgent": is_urgent,
            "due_date": request.form.get("due_date"),
            "created_by": session["user"]
        }
        mongo.db.jobs.insert_one(job)
        flash("Job Successfully Requested")
        return redirect(url_for("home"))

    categories = mongo.db.categories.find().sort("job_category", 1)
    return render_template("request_job.html", categories=categories)


@app.route("/edit_job/<job_id>", methods=["GET", "POST"])
def edit_job(job_id):

    if request.method == "POST":
        is_urgent = "on" if request.form.get("is_urgent") else "off"
        submit = {
            "job_category": request.form.get("job_category"),
            "job_name": request.form.get("job_name"),
            "job_description": request.form.get("job_description"),
            "job_location": request.form.get("job_location"),
            "is_urgent": is_urgent,
            "due_date": request.form.get("due_date"),
            "created_by": session["user"]
        }
        mongo.db.jobs.update({"_id": ObjectId(job_id)}, submit)
        flash("Job Successfully Updated")

    job = mongo.db.jobs.find_one({"_id": ObjectId(job_id)})
    categories = mongo.db.categories.find().sort("job_category", 1)
    return render_template("edit_job.html", job=job, categories=categories)


@app.route("/delete_job/<job_id>")
def delete_job(job_id):
    mongo.db.jobs.remove({"_id": ObjectId(job_id)})
    flash("Job Successfully Deleted")
    return redirect(url_for("home"))


@app.route("/add_comment/<job_id>", methods=["GET", "POST"])
def add_comment(job_id):
    if request.method == "POST":
        comment = request.form.get("comment")
        mongo.db.jobs.update_one({"_id": ObjectId(job_id)},
                                 {"$push": {"comments": comment}})

        return redirect(url_for("get_jobs"))


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=False)
