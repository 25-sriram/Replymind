
import os

from dotenv import load_dotenv
from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    redirect,
    session,
    url_for
)

from ai_engine import analyze_email

from gmail_auth import (
    get_authorization_url,
    get_credentials_from_code,
    save_credentials
)

from gmail_service import (
    fetch_emails,
    get_email_by_id,
    create_gmail_draft
)


load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv("FLASK_SECRET_KEY")

if not app.secret_key:
    raise RuntimeError("FLASK_SECRET_KEY is missing from .env")


# HOME PAGE

@app.route("/")
def home():
    return render_template("index.html")


# MANUAL AI EMAIL GENERATION

@app.route("/generate", methods=["POST"])
def generate():

    try:
        data = request.get_json()

        if not isinstance(data, dict):
            return jsonify({"error": "Invalid request."}), 400

        email = data.get("email", "").strip()
        context = data.get("context", "").strip()
        tone = data.get("tone", "Professional")

        if not email:
            return jsonify({
                "error": "Please enter an email."
            }), 400

        if len(email) > 12000 or len(context) > 3000:
            return jsonify({
                "error": "Input is too long."
            }), 400

        allowed_tones = [
            "Professional",
            "Friendly",
            "Formal",
            "Concise"
        ]

        if tone not in allowed_tones:
            return jsonify({
                "error": "Invalid reply tone."
            }), 400

        result = analyze_email(email, context, tone)

        return jsonify(result)

    except Exception:
        app.logger.exception("Email generation failed")

        return jsonify({
            "error": "Unable to generate reply. Please try again."
        }), 500


# GMAIL AUTHENTICATION

@app.route("/connect-gmail")
def connect_gmail():

    authorization_url, state, code_verifier = get_authorization_url()

    session["oauth_state"] = state
    session["code_verifier"] = code_verifier

    return redirect(authorization_url)


# GMAIL OAUTH CALLBACK

@app.route("/oauth2callback")
def oauth2callback():

    saved_state = session.get("oauth_state")
    received_state = request.args.get("state")

    if not saved_state or saved_state != received_state:
        session.clear()
        return (
            "Invalid OAuth state. Start again from /connect-gmail.",
            400
        )

    code_verifier = session.get("code_verifier")

    if not code_verifier:
        return "Missing code verifier. Please reconnect Gmail.", 400

    code = request.args.get("code")

    if not code:
        return "Authorization code missing.", 400

    try:
        credentials = get_credentials_from_code(
            code,
            code_verifier
        )

        save_credentials(credentials)

        session.clear()

        return redirect(url_for("gmail_inbox"))

    except Exception:
        app.logger.exception("Gmail OAuth callback failed")
        return "Gmail authentication failed.", 500


# GMAIL INBOX

@app.route("/inbox")
def gmail_inbox():

    try:
        emails = fetch_emails()

        return render_template(
            "inbox.html",
            emails=emails
        )

    except Exception:
        app.logger.exception("Gmail inbox loading failed")
        return "Unable to load Gmail inbox.", 500


# ANALYZE EMAIL AND GENERATE REPLY

@app.route("/analyze-gmail/<email_id>", methods=["POST"])
def analyze_gmail(email_id):

    try:
        email_data = get_email_by_id(email_id)

        tone = request.form.get(
            "tone",
            "Professional"
        )

        context = request.form.get(
            "context",
            ""
        ).strip()

        allowed_tones = [
            "Professional",
            "Friendly",
            "Formal",
            "Concise"
        ]

        if tone not in allowed_tones:
            return "Invalid reply tone.", 400

        if len(context) > 3000:
            return "Additional context is too long.", 400

        if not email_data.get("body", "").strip():
            return "This email has no readable text content.", 400

        result = analyze_email(
            email_data["body"],
            context,
            tone
        )

        if not isinstance(result, dict):
            raise ValueError("Invalid AI response.")

        reply_text = result.get("reply", "")

        if not isinstance(reply_text, str) or not reply_text.strip():
            return (
                "AI did not generate a reply. "
                "Check the response structure in ai_engine.py.",
                500
            )

        draft = create_gmail_draft(
            email_data,
            reply_text
        )

        return render_template(
            "analysis.html",
            email=email_data,
            result=result,
            draft_id=draft["id"],
            tone=tone
        )

    except Exception:
        app.logger.exception("Gmail email analysis failed")

        return (
            "Unable to analyze the email or create its draft. "
            "Please check the application error details.",
            500
        )

if __name__ == "__main__":
    app.run(debug=True)
