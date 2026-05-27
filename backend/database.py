import pymysql
import pymysql.cursors
from contextlib import contextmanager

class Database:
    def __init__(self):
        self.connection = None
        self.cursor = None

    def connect(self):
        try:
            self.connection = pymysql.connect(
                host="localhost",
                user="root",
                password="root",
                database="social_analytics",
                port=3308,
                cursorclass=pymysql.cursors.DictCursor
            )
            self.cursor = self.connection.cursor()
            print("Connected to MySQL database")
            return True
        except Exception as err:
            print(f"Database connection error: {err}")
            return False

    def disconnect(self):
        try:
            if self.cursor:
                self.cursor.close()
            if self.connection:
                self.connection.close()
        except Exception as err:
            print(f"Error during disconnect: {err}")

    @contextmanager
    def transaction(self):
        try:
            yield
            self.connection.commit()
        except Exception as err:
            self.connection.rollback()
            raise

    def create_tables(self):
        profiles_ddl = ("CREATE TABLE IF NOT EXISTS profiles ("
            "profile_id INT AUTO_INCREMENT PRIMARY KEY,"
            "username VARCHAR(255) UNIQUE NOT NULL,"
            "display_name VARCHAR(255),"
            "bio TEXT,"
            "followers_count INT,"
            "following_count INT,"
            "account_age_days INT,"
            "ai_profile_risk FLOAT,"
            "fake_profile_risk FLOAT,"
            "account_takeover_risk FLOAT,"
            "overall_risk FLOAT,"
            "incitement_score FLOAT DEFAULT 0,"
            "weighted_extremism_score FLOAT DEFAULT 0,"
            "upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")

        posts_ddl = ("CREATE TABLE IF NOT EXISTS posts ("
            "post_id INT AUTO_INCREMENT PRIMARY KEY,"
            "profile_id INT NOT NULL,"
            "username VARCHAR(255),"
            "post_text LONGTEXT,"
            "post_date DATETIME,"
            "likes INT,"
            "comments INT,"
            "shares INT,"
            "sentiment_score FLOAT,"
            "extremism_score FLOAT,"
            "toxicity_score FLOAT,"
            "misinformation_score FLOAT,"
            "incitement_score FLOAT DEFAULT 0,"
            "weighted_extremism_score FLOAT DEFAULT 0,"
            "proximity_hits TEXT,"
            "upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,"
            "FOREIGN KEY (profile_id) REFERENCES profiles(profile_id) ON DELETE CASCADE)")

        timeline_ddl = ("CREATE TABLE IF NOT EXISTS risk_timeline ("
            "timeline_id INT AUTO_INCREMENT PRIMARY KEY,"
            "profile_id INT NOT NULL,"
            "post_date DATE,"
            "sentiment_score FLOAT,"
            "extremism_score FLOAT,"
            "toxicity_score FLOAT,"
            "incitement_score FLOAT DEFAULT 0,"
            "upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,"
            "FOREIGN KEY (profile_id) REFERENCES profiles(profile_id) ON DELETE CASCADE)")

        tables = {"profiles": profiles_ddl, "posts": posts_ddl, "risk_timeline": timeline_ddl}
        try:
            with self.transaction():
                for table_name, ddl in tables.items():
                    self.cursor.execute(ddl)
                    print(f"Table {table_name} ready")
            print("All tables created successfully")
            return True
        except Exception:
            return False

    def insert_profile(self, profile_data):
        query = ("INSERT INTO profiles "
            "(username, display_name, bio, followers_count, following_count, "
            "account_age_days, ai_profile_risk, fake_profile_risk, "
            "account_takeover_risk, overall_risk) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
            "ON DUPLICATE KEY UPDATE "
            "display_name=VALUES(display_name),bio=VALUES(bio),"
            "followers_count=VALUES(followers_count),following_count=VALUES(following_count),"
            "account_age_days=VALUES(account_age_days),ai_profile_risk=VALUES(ai_profile_risk),"
            "fake_profile_risk=VALUES(fake_profile_risk),"
            "account_takeover_risk=VALUES(account_takeover_risk),overall_risk=VALUES(overall_risk)")
        params = (
            profile_data["username"], profile_data["display_name"], profile_data["bio"],
            profile_data["followers_count"], profile_data["following_count"],
            profile_data["account_age_days"], profile_data["ai_profile_risk"],
            profile_data["fake_profile_risk"], profile_data["account_takeover_risk"],
            profile_data["overall_risk"])
        try:
            with self.transaction():
                self.cursor.execute(query, params)
            return self.cursor.lastrowid
        except Exception:
            return None

    def get_profile_id(self, username):
        try:
            self.cursor.execute("SELECT profile_id FROM profiles WHERE username = %s", (username,))
            result = self.cursor.fetchone()
            return result["profile_id"] if result else None
        except Exception as err:
            print(f"Error looking up profile: {err}")
            return None

    def get_all_profiles(self):
        try:
            self.cursor.execute("SELECT * FROM profiles ORDER BY overall_risk DESC")
            return self.cursor.fetchall()
        except Exception as err:
            print(f"Error retrieving profiles: {err}")
            return []

    def get_profile_details(self, profile_id):
        try:
            self.cursor.execute("SELECT * FROM profiles WHERE profile_id = %s", (profile_id,))
            profile = self.cursor.fetchone()
            if profile:
                self.cursor.execute(
                    "SELECT * FROM posts WHERE profile_id = %s ORDER BY post_date DESC",
                    (profile_id,))
                profile["posts"] = self.cursor.fetchall()
            return profile
        except Exception as err:
            print(f"Error retrieving profile details: {err}")
            return None

    def insert_post(self, post_data):
        profile_id = self.get_profile_id(post_data["username"])
        if not profile_id:
            print(f"No profile found for username: {post_data['username']}")
            return None
        query = ("INSERT INTO posts "
            "(profile_id, username, post_text, post_date, likes, comments, shares, "
            "sentiment_score, extremism_score, toxicity_score, misinformation_score, "
            "incitement_score, weighted_extremism_score, proximity_hits) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
        params = (
            profile_id, post_data["username"], post_data["post_text"],
            post_data["post_date"], post_data["likes"], post_data["comments"],
            post_data["shares"], post_data.get("sentiment_score", 0.0),
            post_data.get("extremism_score", 0.0), post_data.get("toxicity_score", 0.0),
            post_data.get("misinformation_score", 0.0), post_data.get("incitement_score", 0.0),
            post_data.get("weighted_extremism_score", 0.0),
            str(post_data.get("proximity_hits", [])))
        try:
            with self.transaction():
                self.cursor.execute(query, params)
            return self.cursor.lastrowid
        except Exception:
            return None

    def get_risk_timeline(self, profile_id):
        try:
            self.cursor.execute(
                "SELECT * FROM risk_timeline WHERE profile_id = %s ORDER BY post_date ASC",
                (profile_id,))
            return self.cursor.fetchall()
        except Exception as err:
            print(f"Error retrieving timeline: {err}")
            return []

    def insert_timeline_entry(self, profile_id, post_date, scores):
        query = ("INSERT INTO risk_timeline "
            "(profile_id, post_date, sentiment_score, extremism_score, "
            "toxicity_score, incitement_score) VALUES (%s, %s, %s, %s, %s, %s)")
        params = (profile_id, post_date, scores.get("sentiment_score", 0.0),
            scores.get("extremism_score", 0.0), scores.get("toxicity_score", 0.0),
            scores.get("incitement_score", 0.0))
        try:
            with self.transaction():
                self.cursor.execute(query, params)
            return True
        except Exception:
            return False

    def clear_all_data(self):
        try:
            with self.transaction():
                for table in ("posts", "risk_timeline", "profiles"):
                    self.cursor.execute(f"DELETE FROM {table}")
            print("All data cleared")
            return True
        except Exception:
            return False
