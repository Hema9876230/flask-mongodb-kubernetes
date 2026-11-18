
import os
import logging
from datetime import datetime, timezone
from urllib.parse import quote_plus

from flask import Flask, request, jsonify
from pymongo import MongoClient
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError


# --------------------------------------------------
# 1. Flask Application Configuration
# --------------------------------------------------

app = Flask(__name__)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)

logger = logging.getLogger(__name__)


# --------------------------------------------------
# 2. MongoDB Configuration
# --------------------------------------------------

MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
MONGO_PORT = os.getenv("MONGO_PORT", "27017")

MONGO_USERNAME = os.getenv("MONGO_USERNAME")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")

DATABASE_NAME = os.getenv("MONGO_DATABASE", "flask_db")


def build_mongodb_uri():

    if MONGO_USERNAME and MONGO_PASSWORD:

        username = quote_plus(MONGO_USERNAME)
        password = quote_plus(MONGO_PASSWORD)

        return (
            f"mongodb://{username}:{password}"
            f"@{MONGO_HOST}:{MONGO_PORT}/{DATABASE_NAME}"
            "?authSource=admin"
        )

    return os.getenv(
        "MONGODB_URI",
        f"mongodb://{MONGO_HOST}:{MONGO_PORT}/{DATABASE_NAME}"
    )


MONGODB_URI = build_mongodb_uri()


# --------------------------------------------------
# 3. MongoDB Client
# --------------------------------------------------

client = MongoClient(
    MONGODB_URI,
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=5000,
    socketTimeoutMS=10000,
    maxPoolSize=50,
    minPoolSize=2,
    retryWrites=True
)

db = client[DATABASE_NAME]

collection = db["data"]


# --------------------------------------------------
# 4. Root Endpoint
# --------------------------------------------------

@app.route("/", methods=["GET"])
def index():

    return (
        f"Welcome to the Flask app! "
        f"The current time is: {datetime.now()}"
    ), 200


# --------------------------------------------------
# 5. Liveness Probe
# --------------------------------------------------

@app.route("/live", methods=["GET"])
def live():

    return jsonify({
        "status": "alive",
        "service": "flask-app"
    }), 200


# --------------------------------------------------
# 6. Readiness / Database Health Probe
# --------------------------------------------------

@app.route("/health", methods=["GET"])
def health():

    try:

        client.admin.command("ping")

        return jsonify({
            "status": "healthy",
            "database": "connected"
        }), 200

    except PyMongoError:

        logger.exception("MongoDB health check failed")

        return jsonify({
            "status": "unhealthy",
            "database": "disconnected"
        }), 503


# --------------------------------------------------
# 7. Insert and Retrieve Data
# --------------------------------------------------

@app.route("/data", methods=["GET", "POST"])
def data():

    # POST: Insert a document into MongoDB

    if request.method == "POST":

        payload = request.get_json(silent=True)

        if not isinstance(payload, dict) or not payload:

            return jsonify({
                "error": "A valid non-empty JSON object is required"
            }), 400

        try:

            payload["created_at"] = datetime.now(
                timezone.utc
            ).isoformat()

            result = collection.insert_one(payload)

            logger.info(
                "Document inserted successfully: %s",
                result.inserted_id
            )

            return jsonify({
                "status": "Data inserted successfully",
                "inserted_id": str(result.inserted_id)
            }), 201

        except PyMongoError:

            logger.exception("MongoDB insertion failed")

            return jsonify({
                "error": "Database insertion failed"
            }), 500

    # GET: Retrieve all documents

    try:

        records = list(
            collection.find({}, {"_id": 0})
        )

        return jsonify(records), 200

    except PyMongoError:

        logger.exception("MongoDB retrieval failed")

        return jsonify({
            "error": "Database retrieval failed"
        }), 500


# --------------------------------------------------
# 8. Application Startup
# --------------------------------------------------

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
