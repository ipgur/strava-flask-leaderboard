
# Strava Flask Leaderboard

## Overview

A simple Flask-based application that fetches Strava data and displays a leaderboard based on Year-To-Date (YTD) running stats, including total distance, number of runs, and total time. Users can authenticate via Strava OAuth and view the leaderboard with their achievements and medals (Gold, Silver, Bronze).

## Features

- **User Authentication**: OAuth authentication via Strava API.
- **Leaderboard**: Display YTD running stats for each user.
- **Medals**: Users are awarded Gold, Silver, or Bronze medals based on their ranking.
- **User Avatars**: Show the avatar of each user next to their name.
- **Deployment on Heroku**: A Heroku-compatible app with automatic database migrations using `Flask-Migrate`.

## Requirements

- Python 3.x
- Flask
- Flask-SQLAlchemy
- Flask-Migrate
- psycopg2-binary (for PostgreSQL support)
- requests
- gunicorn (for production deployment)
- python-dotenv (for managing environment variables)
- OAuth via Strava API

## Setup

### Local Development Setup

1. Clone the repository:

2. Create a virtual environment:

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scriptsctivate
    ```

3. Install the required dependencies:

    ```bash
    pip install -r requirements.txt
    ```

4. Set up your `.env` file with the following environment variables:

    ```env
    STRAVA_CLIENT_ID=your_strava_client_id
    STRAVA_CLIENT_SECRET=your_strava_client_secret
    STRAVA_REDIRECT_URI=http://localhost:5000/callback  # Update for production
    DATABASE_URL=your_postgresql_database_url  # e.g., from Heroku or local PostgreSQL
    ```

5. Run the application locally:

    ```bash
    flask run
    ```

6. Visit `http://localhost:5000` to authenticate via Strava and see the leaderboard.

### Deploy to Heroku

1. Create a Heroku app:

    ```bash
    heroku create
    ```

2. Set the required environment variables on Heroku:

    ```bash
    heroku config:set STRAVA_CLIENT_ID=your_strava_client_id
    heroku config:set STRAVA_CLIENT_SECRET=your_strava_client_secret
    heroku config:set STRAVA_REDIRECT_URI=https://your-app.herokuapp.com/callback
    heroku config:set DATABASE_URL=your_postgresql_database_url
    ```

3. Deploy to Heroku:

    ```bash
    git push heroku master
    ```

4. Open your app in the browser:

    ```bash
    heroku open
    ```