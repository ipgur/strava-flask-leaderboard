import os
import requests
from flask import Flask, redirect, request, session, url_for, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, timedelta
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev")

# DB setup
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv('DATABASE_URL', 'sqlite:///strava_users.db').replace('postgres://', 'postgresql://')
print(app.config["SQLALCHEMY_DATABASE_URI"])
db = SQLAlchemy(app)
migrate = Migrate(app, db)


# Strava config
CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")


# Models
class StravaUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    strava_id = db.Column(db.Integer, unique=True, nullable=False)
    firstname = db.Column(db.String)
    lastname = db.Column(db.String)
    access_token = db.Column(db.String)
    refresh_token = db.Column(db.String)
    token_expires_at = db.Column(db.DateTime)


# Get the current year
current_year = datetime.now().year


# Routes
@app.route("/register")
def index():
    return render_template("register.html")


@app.route("/login")
def login():
    auth_url = (
        f"https://www.strava.com/oauth/authorize?client_id={CLIENT_ID}"
        f"&response_type=code&redirect_uri={REDIRECT_URI}"
        f"&approval_prompt=auto&scope=activity:read_all"
    )
    return redirect(auth_url)


@app.route("/authorized")
def authorized():
    code = request.args.get("code")
    token_url = "https://www.strava.com/oauth/token"
    response = requests.post(token_url, data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code"
    })

    data = response.json()
    access_token = data["access_token"]
    refresh_token = data["refresh_token"]
    expires_at = datetime.utcfromtimestamp(data["expires_at"])
    athlete = data["athlete"]

    user = StravaUser.query.filter_by(strava_id=athlete["id"]).first()
    if not user:
        user = StravaUser(strava_id=athlete["id"])
    user.firstname = athlete["firstname"]
    user.lastname = athlete["lastname"]
    user.access_token = access_token
    user.refresh_token = refresh_token
    user.token_expires_at = expires_at
    db.session.add(user)
    db.session.commit()

    return redirect(url_for("all_stats"))


@app.route("/")
def all_stats():
    users = StravaUser.query.all()
    stats = []

    for user in users:
        if user.token_expires_at < datetime.utcnow():
            token_url = "https://www.strava.com/oauth/token"
            resp = requests.post(token_url, data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "grant_type": "refresh_token",
                "refresh_token": user.refresh_token,
            })
            t = resp.json()
            user.access_token = t["access_token"]
            user.refresh_token = t["refresh_token"]
            user.token_expires_at = datetime.utcfromtimestamp(t["expires_at"])
            db.session.commit()

        r = requests.get(
            "https://www.strava.com/api/v3/athletes/{}/stats".format(user.strava_id),
            headers={"Authorization": f"Bearer {user.access_token}"}
        )

        if r.status_code == 200:
            data  = r.json()
            print(data)  # Add this line to inspect the structure		    

            # Get YTD running totals
            ytd_run_totals = data.get('ytd_run_totals', {})
            print(ytd_run_totals)

            # Extract total distance for the current year in meters
            total_meters = ytd_run_totals.get('distance', 0)
            total_runs = ytd_run_totals.get('count', 0)
            total_time = ytd_run_totals.get('moving_time', 0) / 3600

            # Convert meters to kilometers
            total_kms = total_meters / 1000  # Convert meters to kilometers
            stats.append({
                "name": f"{user.firstname} {user.lastname}",
                "kms": round(total_kms, 2),  # Round to 2 decimal places
                "count": round(total_runs, 2),  # Round to 2 decimal places
                "time": round(total_time, 2),  # Round to 2 decimal places
            }) 
    # Sort stats by 'kms' in descending order (highest kilometers first)
    stats.sort(key=lambda x: x["kms"], reverse=True)
    return render_template("home.html", stats=stats)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)

