# ATC Monitor

ATC Monitor is an aviation radio communications analysis platform that ingests ATC audio recordings, transcribes them using speech recognition with aviation domain adaptation, and performs intelligent post-processing to extract callsigns, operators, routes, and speaker roles (Controller vs Pilot).

## Vision

The goal is to build a comprehensive ATC monitoring solution that:

- **Captures and transcribes** ATC audio from multiple sources (RF/VHF antenna feeds, IP streams, recorded files)
- **Extracts structured data** from unstructured radio communications (callsigns, instructions, readbacks)
- **Links conversations** by grouping messages into threads based on callsign and time windows
- **Analyzes quality** of communications (accent clarity, speech rate, excessive repeats)
- **Alerts on anomalies** such as potential safety issues, go-arounds, emergency calls, or unusual patterns
- **Integrates with flight tracking** services (FlightRadar24, FlightAware, ADS-B Exchange) to correlate audio with aircraft positions

## Architecture

```
+------------------+     +-------------------+     +------------------+
|  Audio Ingestion |---->|  Pre-processing   |---->|  ASR Engine      |
|  (RF/IP/File)    |     |  (AGC/Denoise/VAD)|     |  (Whisper+Domain)|
+------------------+     +-------------------+     +------------------+
                                                           |
                                                           v
+------------------+     +-------------------+     +------------------+
|  UI / Alerts /   |<----|  Storage Layer    |<----|  Post-processing |
|  API / Replay    |     |  (SQLite/Archive) |     |  (Callsign/Speaker)
+------------------+     +-------------------+     +------------------+
```

### Pipeline Stages

1. **Audio Ingestion** - Capture from one or many simultaneous RF/VHF streams, IP streams, or file uploads
2. **Pre-processing** - AGC, gain normalization, noise reduction, VAD (Voice Activity Detection), channel separation
3. **ASR + Domain Adaptation** - Speech-to-text with callsign-aware decoder and aviation vocabulary
4. **Post-processing** - Text normalization, punctuation restoration, callsign extraction, sentence segmentation, speaker diarization (controller vs pilot)
5. **Conversation Linking** - Group messages into threads by callsign and date/time window
6. **Storage** - Transcript database, audio archive, metadata indexing
7. **UI / Alerting** - Live monitoring dashboard, anomaly alerts, audio replay, API for external integration
8. **Logging & Audit** - Comprehensive audit trail for compliance and debugging

## Project Structure

```
atc-monitor/
├── main.py                 # CLI entry point
├── processor/
│   ├── db.py              # Database layer
│   └── postprocess.py     # Callsign/speaker extraction
├── web/
│   ├── webapp.py          # Flask web interface
│   └── templates/
│       └── index.html     # Message display template
├── callsigns.csv          # Airline callsign mappings
├── requirements.txt       # Python dependencies
└── .env.example           # Environment template
```

## Quick Start

```bash
# Clone the repository
git clone https://github.com/Spudwars/atc-monitor.git
cd atc-monitor

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Initialize database
python main.py

# Re-analyze existing messages
python main.py --reanalyze

# Run web interface
python -m web.webapp
```

## Current Status

This project is in early development. Current capabilities:

- [x] SQLite database schema for messages
- [x] Basic speaker detection (Tower vs Aircraft) via keyword matching
- [x] Callsign CSV mapping file structure
- [x] Flask web interface for viewing messages
- [ ] Audio ingestion pipeline
- [ ] Whisper transcription integration
- [ ] Callsign extraction from message text
- [ ] Conversation threading

## TODO

### Phase 1: Foundation (Current)

- [ ] **Callsign Extraction** - Implement regex + fuzzy matching to extract callsigns from transcribed text
- [ ] **Database Migrations** - Add Alembic or custom migration scripts for schema evolution
- [ ] **DB Layer Consistency** - Centralize all database access through a single module with connection pooling
- [ ] **Caching Layer** - Add caching for callsign lookups and repeated queries
- [ ] **Test Infrastructure** - Set up pytest with fixtures for database and processing tests
- [ ] **CI/CD Pipeline** - GitHub Actions for linting, testing, and deployment

### Phase 2: Transcription

- [ ] **Whisper Integration** - Integrate faster-whisper for local transcription
- [ ] **Aviation Vocabulary** - Fine-tune or prompt-engineer for aviation terminology (phonetic alphabet, standard phraseology)
- [ ] **Audio Pre-processing** - Implement AGC, noise reduction, and VAD
- [ ] **Batch Processing** - Process recorded audio files in bulk
- [ ] **Confidence Scoring** - Track transcription confidence per segment

### Phase 3: Intelligence

- [ ] **Conversation Threading** - Link messages by callsign within configurable time windows
- [ ] **Speaker Diarization** - Improve controller vs pilot detection using audio features
- [ ] **Sentiment Analysis** - Detect stress, urgency, or confusion in communications
- [ ] **Quality Metrics** - Measure speech rate, accent clarity, repeat frequency
- [ ] **Anomaly Detection** - Flag go-arounds, emergencies, unusual instructions

### Phase 4: Integration

- [ ] **ADS-B Integration** - Correlate audio with aircraft positions from FlightRadar24/FlightAware APIs
- [ ] **Live Streaming** - Real-time processing of live audio feeds
- [ ] **Alert System** - Configurable alerts for keywords, callsigns, or anomalies
- [ ] **Audio Replay** - Jump to specific timestamps in archived audio
- [ ] **REST API** - Expose data for external tools and dashboards

### Phase 5: Scale

- [ ] **Cloud Deployment** - AWS/GCP architecture for production workloads
- [ ] **Audio Pipeline** - AWS Transcribe or similar for scalable ASR
- [ ] **Multi-frequency** - Handle multiple simultaneous ATC frequencies
- [ ] **Historical Analysis** - Trend analysis across days/weeks/months
- [ ] **Export Formats** - CSV, JSON, industry-standard formats for analysis

## Key Challenges

- **Audio Quality** - ATC radio has variable volume, background noise, squelch, and overlapping transmissions
- **Accents & Speed** - Controllers and pilots speak rapidly with various accents
- **Domain Vocabulary** - Aviation phraseology, phonetic alphabet (Alpha, Bravo...), non-standard callsigns
- **Speaker Separation** - Distinguishing controller from pilot without explicit turn indicators
- **Callsign Variants** - Same airline may use different callsign formats (SPEEDBIRD 123, BA123, British 123)

## Contributing

This project is structured for iterative development. Contributions welcome for:

- Aviation domain expertise (phraseology, callsign databases)
- Audio processing (noise reduction, VAD algorithms)
- ML/ASR improvements (fine-tuning, prompt engineering)
- Integration connectors (ADS-B APIs, flight tracking)

## License

MIT License - See LICENSE file for details.
