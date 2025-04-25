import os
import requests
import polyline

from flask import Flask, redirect, request, session, url_for, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev")

# DB setup
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv('DATABASE_URL', 'sqlite:///strava_users.db').replace("postgres://", "postgresql://")
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
    user_runs = []
    for user in users:

        if user.token_expires_at < datetime.utcnow():
            token_url = "https://www.strava.com/oauth/token"
            resp = requests.post(token_url, data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "grant_type": "refresh_token",
                "refresh_token": user.refresh_token,
            })

            if resp.status_code != 200:
                print(f"Skipping user {user.id}: failed to refresh token (status {resp.status_code})")
                continue  # Skip this user
            try:
                t = resp.json()
                user.access_token = t["access_token"]
                user.refresh_token = t["refresh_token"]
                user.token_expires_at = datetime.utcfromtimestamp(t["expires_at"])
                db.session.commit()
            except (KeyError, ValueError) as e:
                print(f"Skipping user {user.id}: invalid token response: {e}")
                continue

        # Get athlete profile (for avatar, name, etc.)
        athlete_response = requests.get(
            "https://www.strava.com/api/v3/athlete",
            headers={"Authorization": f"Bearer {user.access_token}"}
        )

        # Get athlete stats (run distance, etc.)
        stats_response = requests.get(
            f"https://www.strava.com/api/v3/athletes/{user.strava_id}/stats",
            headers={"Authorization": f"Bearer {user.access_token}"}
        )

        # Fetch the latest activities (1 activity, sorted by date)
        activity_url = 'https://www.strava.com/api/v3/athlete/activities'
        params = {'per_page': 5, 'page': 1}
        activities_response = requests.get(activity_url, headers={"Authorization": f"Bearer {user.access_token}"}, params=params)

        if (athlete_response.status_code == 200 and stats_response.status_code == 200 and
                activities_response.status_code == 200):
            athlete = athlete_response.json()
            data = stats_response.json()
            activities = activities_response.json()
            # Extract YTD run stats
            ytd_run_totals = data.get('ytd_run_totals', {})
            elevation_gain = ytd_run_totals.get('elevation_gain', 0)
            total_meters = ytd_run_totals.get('distance', 0)
            total_runs = ytd_run_totals.get('count', 0)
            total_time = ytd_run_totals.get('moving_time', 0) / 3600

            # Convert meters to kilometers
            total_kms = total_meters / 1000

            stats.append({
                "name": f"{athlete.get('firstname')} {athlete.get('lastname')}",
                "avatar": athlete.get("profile_medium"),  # or "profile" for larger
                "kms": round(total_kms, 2),
                "elev_gain": round(elevation_gain, 2),
                "count": round(total_runs, 2),
                "time": round(total_time, 2),
            })

            # Get the latest run activity and decode the polyline
            latest_run = None
            for activity in activities:
                if activity['type'] == 'Run' and  activity['start_date'].startswith(str(current_year)):
                    latest_run = activity
                    #print(latest_run)
                    break  # Stop once the latest run is found

            if latest_run:
                polyline_str = latest_run['map']['summary_polyline']
                decoded_polyline = polyline.decode(polyline_str)
                user_runs.append({'user': f"{athlete.get('firstname')} {athlete.get('lastname')}",
                                  "avatar": athlete.get("profile"),
                                  'run': latest_run,
                                  'coordinates': decoded_polyline})
            print(user_runs)

    # Sort runs by start_date most recent first
    sorted_runs = sorted(user_runs, key=lambda x: x['run']['start_date'], reverse=True)
    # Sort stats by 'kms' in descending order (highest kilometers first)
    stats.sort(key=lambda x: x["kms"], reverse=True)
    for i, s in enumerate(stats, 1):
        print(f"{i}. {s['name']} - {s['kms']} km")
    return render_template("home.html", stats=stats, user_runs=sorted_runs, current_year=current_year)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)

