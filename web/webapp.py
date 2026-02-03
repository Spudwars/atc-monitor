"""
Flask web interface for ATC Monitor.

Provides:
- Dashboard with recent messages
- Tower view with live polling
- Operator view
- Conversation threading by callsign
- Search with autosuggest
- CSV/JSON export
- Audio playback
"""

import csv
import io
from flask import Flask, render_template, request, send_from_directory, jsonify, make_response

from processor.db import query_all, query_one

app = Flask(__name__)

# Audio files directory
AUDIO_DIR = "audio"


def get_messages_query(
    limit: int = 100,
    offset: int = 0,
    callsign: str = None,
    speaker: str = None,
    operator: str = None,
    airport: str = None,
    keyword: str = None,
    start_date: str = None,
    end_date: str = None,
    search: str = None,
) -> list:
    """Build and execute a filtered messages query."""
    conditions = []
    params = []

    if callsign:
        conditions.append("callsign = ?")
        params.append(callsign)
    if speaker:
        conditions.append("speaker = ?")
        params.append(speaker)
    if operator:
        conditions.append("operator = ?")
        params.append(operator)
    if airport:
        conditions.append("airport = ?")
        params.append(airport)
    if keyword:
        conditions.append("keywords LIKE ?")
        params.append(f"%{keyword}%")
    if start_date:
        conditions.append("timestamp_start >= ?")
        params.append(float(start_date) if start_date.replace('.','').isdigit() else 0)
    if end_date:
        conditions.append("timestamp_end <= ?")
        params.append(float(end_date) if end_date.replace('.','').isdigit() else 999999)
    if search:
        conditions.append("(message LIKE ? OR callsign LIKE ? OR operator LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    sql = f"""
        SELECT * FROM messages
        {where_clause}
        ORDER BY id DESC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])

    return query_all(sql, tuple(params))


# Serve audio files
@app.route("/audio/<filename>")
def audio_file(filename):
    """Serve audio files for playback."""
    return send_from_directory(AUDIO_DIR, filename)


# Dashboard - recent messages
@app.route("/")
def index():
    """Display recent messages with search."""
    search = request.args.get("q", "").strip()
    messages = get_messages_query(limit=50, search=search if search else None)

    # Get suggestions for autocomplete
    suggestions = []
    if search:
        suggestions_rows = query_all(
            "SELECT DISTINCT callsign FROM messages WHERE callsign LIKE ? LIMIT 10",
            (f"%{search}%",)
        )
        suggestions = [r['callsign'] for r in suggestions_rows if r['callsign']]

    return render_template("index.html", messages=messages, suggestions=suggestions, search=search)


# Tower view - messages for a specific airport
@app.route("/tower/<airport>")
def tower(airport):
    """Display messages for a specific airport with live polling."""
    messages = get_messages_query(limit=100, airport=airport.upper())
    return render_template("tower.html", messages=messages, airport=airport.upper())


# Operator view - messages for a specific airline
@app.route("/operator/<operator>")
def operator_page(operator):
    """Display messages for a specific operator/airline."""
    messages = get_messages_query(limit=100, operator=operator)
    return render_template("operator.html", messages=messages, operator=operator)


# Conversation view - messages for a specific callsign
@app.route("/conversation/<callsign>")
def conversation(callsign):
    """Display conversation thread for a specific callsign."""
    messages = query_all(
        "SELECT * FROM messages WHERE callsign = ? ORDER BY id ASC",
        (callsign.upper(),)
    )
    return render_template("conversation.html", messages=messages, callsign=callsign.upper())


# Search endpoint
@app.route("/search")
def search():
    """Search messages with filters."""
    q = request.args.get("q", "").strip()
    messages = get_messages_query(limit=100, search=q if q else None)

    suggestions = []
    if q:
        suggestions_rows = query_all(
            "SELECT DISTINCT callsign FROM messages WHERE callsign LIKE ? LIMIT 10",
            (f"%{q}%",)
        )
        suggestions = [r['callsign'] for r in suggestions_rows if r['callsign']]

    return render_template("index.html", messages=messages, suggestions=suggestions, search=q)


# Export endpoint - CSV/JSON
@app.route("/export")
def export_data():
    """Export filtered messages as CSV or JSON."""
    operator = request.args.get("operator")
    airport = request.args.get("airport")
    keyword = request.args.get("keyword")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    fmt = request.args.get("format", "csv")

    messages = get_messages_query(
        limit=10000,
        operator=operator,
        airport=airport,
        keyword=keyword,
        start_date=start_date,
        end_date=end_date,
    )

    if fmt == "json":
        return jsonify([dict(m) for m in messages])
    else:
        # CSV export
        output = io.StringIO()
        if messages:
            writer = csv.DictWriter(output, fieldnames=messages[0].keys())
            writer.writeheader()
            for m in messages:
                writer.writerow(dict(m))

        response = make_response(output.getvalue())
        response.headers["Content-Disposition"] = "attachment; filename=atc_export.csv"
        response.headers["Content-Type"] = "text/csv"
        return response


# API endpoints

@app.route("/api/messages")
def api_messages():
    """JSON API for messages with filters."""
    messages = get_messages_query(
        limit=request.args.get("limit", 100, type=int),
        offset=request.args.get("offset", 0, type=int),
        callsign=request.args.get("callsign"),
        speaker=request.args.get("speaker"),
        operator=request.args.get("operator"),
        airport=request.args.get("airport"),
        keyword=request.args.get("keyword"),
    )
    return jsonify({
        "messages": [dict(m) for m in messages],
        "count": len(messages),
    })


@app.route("/api/poll/<airport>")
def poll_tower(airport):
    """Polling endpoint for live tower updates."""
    last_id = request.args.get("last_id", 0, type=int)

    messages = query_all(
        "SELECT * FROM messages WHERE airport = ? AND id > ? ORDER BY id ASC",
        (airport.upper(), last_id)
    )

    return jsonify([dict(m) for m in messages])


@app.route("/api/stats")
def api_stats():
    """Get statistics about the message database."""
    total = query_one("SELECT COUNT(*) as count FROM messages")
    by_speaker = query_all(
        "SELECT speaker, COUNT(*) as count FROM messages GROUP BY speaker"
    )
    by_airport = query_all(
        "SELECT airport, COUNT(*) as count FROM messages WHERE airport IS NOT NULL GROUP BY airport ORDER BY count DESC LIMIT 10"
    )
    by_operator = query_all(
        "SELECT operator, COUNT(*) as count FROM messages WHERE operator IS NOT NULL GROUP BY operator ORDER BY count DESC LIMIT 10"
    )
    with_keywords = query_one(
        "SELECT COUNT(*) as count FROM messages WHERE keywords IS NOT NULL AND keywords != ''"
    )

    return jsonify({
        "total_messages": total["count"] if total else 0,
        "by_speaker": {r["speaker"]: r["count"] for r in by_speaker if r["speaker"]},
        "by_airport": {r["airport"]: r["count"] for r in by_airport if r["airport"]},
        "by_operator": {r["operator"]: r["count"] for r in by_operator if r["operator"]},
        "with_keywords": with_keywords["count"] if with_keywords else 0,
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
