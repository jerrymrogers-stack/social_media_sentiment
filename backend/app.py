# app.py
# Flask application entry point and API routes

import os
import sys
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from config import MAX_FILE_SIZE, ALLOWED_FORMATS
from database import Database
from file_handler import FileHandler
from analyzer import Analyzer

# ---------------------------------------------------------------------------
# APP SETUP
# ---------------------------------------------------------------------------

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend'), static_url_path='')
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

db = Database()

# ---------------------------------------------------------------------------
# STARTUP
# ---------------------------------------------------------------------------

def initialize():
    print("=" * 60)
    print("Starting Social Media Analytics Tool...")
    print("=" * 60)

    if not db.connect():
        print("✗ Failed to connect to database. Exiting.")
        sys.exit(1)

    if not db.create_tables():
        print("✗ Failed to create database tables. Exiting.")
        sys.exit(1)

    print("✓ Database initialized successfully")
    print("=" * 60)
    print("Dashboard available at: http://localhost:5000")
    print("=" * 60)

# ---------------------------------------------------------------------------
# FRONTEND ROUTE
# ---------------------------------------------------------------------------

@app.route('/')
def serve_frontend():
    return send_from_directory(
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend'),
        'index.html'
    )

# ---------------------------------------------------------------------------
# API: UPLOAD
# ---------------------------------------------------------------------------

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400

    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext not in ALLOWED_FORMATS:
        return jsonify({
            'success': False,
            'error':   f'Unsupported format. Allowed: {", ".join(ALLOWED_FORMATS)}'
        }), 400

    # Save temp file
    temp_path = f'temp_upload.{ext}'
    try:
        file.save(temp_path)
        df = FileHandler.load_file(temp_path)

        if df is None:
            return jsonify({'success': False, 'error': 'Failed to parse file'}), 400

        profiles_count = 0
        posts_count    = 0

        for username, group in df.groupby('username'):
            profile_data = {
                'username':             username,
                'display_name':         group['display_name'].iloc[0],
                'bio':                  group['bio'].iloc[0],
                'followers_count':      int(group['followers_count'].iloc[0]),
                'following_count':      int(group['following_count'].iloc[0]),
                'account_age_days':     int(group['account_age_days'].iloc[0]),
                'ai_profile_risk':      0.0,
                'fake_profile_risk':    0.0,
                'account_takeover_risk':0.0,
                'overall_risk':         0.0,
            }

            # Analyze posts
            post_records = []
            for _, row in group.iterrows():
                scores = Analyzer.analyze_post(row['post_text'])
                post_records.append({
                    'username':             username,
                    'post_text':            row['post_text'],
                    'post_date':            row['post_date'],
                    'likes':                int(row['likes']),
                    'comments':             int(row['comments']),
                    'shares':               int(row['shares']),
                    **scores
                })

            # Profile-level risk
            import pandas as pd
            posts_df     = pd.DataFrame(post_records)
            profile_risk = Analyzer.analyze_profile(posts_df, profile_data)
            profile_data.update(profile_risk)

            # Write to DB
            profile_id = db.insert_profile(profile_data)
            if profile_id:
                profiles_count += 1
                for post in post_records:
                    if db.insert_post(post):
                        posts_count += 1

        return jsonify({
            'success':        True,
            'profiles_count': profiles_count,
            'posts_count':    posts_count,
        })

    except Exception as e:
        print(f"✗ Upload error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

# ---------------------------------------------------------------------------
# API: PROFILES
# ---------------------------------------------------------------------------

@app.route('/api/profiles', methods=['GET'])
def get_profiles():
    try:
        profiles = db.get_all_profiles()
        return jsonify({'success': True, 'profiles': profiles})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/profiles/<int:profile_id>', methods=['GET'])
def get_profile(profile_id):
    try:
        profile = db.get_profile_details(profile_id)
        if not profile:
            return jsonify({'success': False, 'error': 'Profile not found'}), 404
        return jsonify({'success': True, 'profile': profile})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ---------------------------------------------------------------------------
# API: TIMELINE
# ---------------------------------------------------------------------------

@app.route('/api/profiles/<int:profile_id>/timeline', methods=['GET'])
def get_timeline(profile_id):
    try:
        timeline = db.get_risk_timeline(profile_id)
        return jsonify({'success': True, 'timeline': timeline})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ---------------------------------------------------------------------------
# API: UTILITY
# ---------------------------------------------------------------------------

@app.route('/api/clear', methods=['POST'])
def clear_data():
    try:
        db.clear_all_data()
        return jsonify({'success': True, 'message': 'All data cleared'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'success': True, 'status': 'running'})

# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    initialize()
    app.run(debug=True, host='0.0.0.0', port=5000)