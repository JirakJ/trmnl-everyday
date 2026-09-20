"""Private confirmation service. A GET never completes a task."""
import argparse
import secrets
from urllib.parse import urlsplit
from flask import Flask, abort, redirect, render_template_string, request, session
from waitress import serve
from .common import clock, read_config
from .maintenance import action_task, base_url, complete, database, due_date, last_done, tasks

PAGE = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Home Maintenance</title>
<style>body{font:18px/1.5 system-ui;max-width:34rem;margin:4rem auto;padding:0 1.5rem;color:#172328;background:#f7f7f2}
h1{font-size:2rem}button{font:inherit;padding:1rem;border:0;border-radius:.5rem;background:#172328;color:white;cursor:pointer}
small{color:#445459}</style><main><small>HOME MAINTENANCE</small><h1>{{ name }}</h1>
<p>{{ message }}</p>{% if csrf %}<form method="post"><input type="hidden" name="csrf" value="{{ csrf }}">
<button type="submit">Mark completed today</button></form>{% endif %}</main></html>"""


def create_app(config, now_fn=None):
    tasks(config)
    origin = base_url(config)
    now_fn = now_fn or (lambda: clock(config))
    with database(config) as db:
        db.execute("INSERT OR IGNORE INTO settings VALUES ('session_key', ?)", (secrets.token_hex(32),))
        key = db.execute("SELECT value FROM settings WHERE key='session_key'").fetchone()[0]
    app = Flask(__name__, static_folder=None)
    app.config.update(SECRET_KEY=key, MAX_CONTENT_LENGTH=2048, MAX_FORM_MEMORY_SIZE=2048,
                      MAX_FORM_PARTS=4, SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Strict",
                      SESSION_COOKIE_SECURE=origin.startswith("https:"), TRUSTED_HOSTS=[urlsplit(origin).hostname])

    @app.after_request
    def secure_headers(response):
        response.headers.update({"Cache-Control": "no-store", "Referrer-Policy": "same-origin",
                                 "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY",
                                 "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"})
        return response

    @app.route("/complete/<token>", methods=["GET", "POST"])
    def confirmation(token):
        now = now_fn()
        if request.method == "POST":
            csrf = session.get("csrf", "")
            if not csrf or not secrets.compare_digest(csrf, request.form.get("csrf", "")):
                abort(403)
            if request.headers.get("Origin") not in (None, origin):
                abort(403)
            try:
                task = complete(config, token, now)
            except ValueError:
                abort(410)
            session.pop("csrf", None)
            session["saved"] = task["name"]
            return redirect("/saved", code=303)
        try:
            with database(config) as db:
                task = action_task(db, config, token, now)
                due = due_date(task, last_done(db, task))
        except ValueError:
            abort(410)
        session["csrf"] = secrets.token_urlsafe(24)
        message = f"Due {due:%d %b %Y}. Confirm only after finishing the task. The next interval starts today."
        return render_template_string(PAGE, name=task["name"], message=message, csrf=session["csrf"])

    @app.get("/saved")
    def saved():
        if "saved" not in session:
            abort(404)
        return render_template_string(PAGE, name=session["saved"], message="Saved. Your display will update when the collector runs again.", csrf=None)

    @app.errorhandler(410)
    def expired(error):
        return render_template_string(PAGE, name="This link is no longer valid", message="The task may already be completed. Refresh the display and scan its current QR code.", csrf=None), 410

    return app


def main():
    parser = argparse.ArgumentParser(description="Run the private maintenance confirmation service")
    parser.add_argument("--config", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    config = read_config(args.config)
    serve(create_app(config), host=args.host, port=args.port, max_request_body_size=2048,
          max_request_header_size=8192, channel_timeout=30, connection_limit=32)


if __name__ == "__main__":
    main()
