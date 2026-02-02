"""
Flask web interface for ATC Monitor.

Provides a simple UI to view transcribed messages.
"""

from flask import Flask, render_template, request

from processor.db import get_messages, readonly

app = Flask(__name__)


@app.route("/")
def index():
    """Display recent messages with optional filters."""
    # Get filter parameters
    callsign = request.args.get('callsign')
    speaker = request.args.get('speaker')
    limit = request.args.get('limit', 100, type=int)

    messages = get_messages(
        limit=limit,
        callsign=callsign,
        speaker=speaker,
    )

    return render_template("index.html", messages=messages)


@app.route("/api/messages")
def api_messages():
    """JSON API for messages."""
    callsign = request.args.get('callsign')
    speaker = request.args.get('speaker')
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)

    messages = get_messages(
        limit=limit,
        offset=offset,
        callsign=callsign,
        speaker=speaker,
    )

    return {
        'messages': [dict(m) for m in messages],
        'count': len(messages),
    }


if __name__ == "__main__":
    app.run(debug=True)
