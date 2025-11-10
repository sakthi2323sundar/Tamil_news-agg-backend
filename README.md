# Tamil News Aggregator

Backend (Python) and Frontend (React + Vite) for aggregating Tamil news from multiple sources.

## Features
- Scrapes multiple Tamil news sources
- REST API to fetch aggregated articles
- Admin trigger to run a manual fetch
- React frontend to browse latest news

## Prerequisites
- Python 3.11+
- Node.js 18+

## Backend Setup
```bash
# Create and activate virtual environment
python -m venv venv
# Windows PowerShell
./venv/Scripts/Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run the server (adjust command if different)
python app/main.py
```

## Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## Environment Variables
Create a `.env` in the backend root if needed. Example:
```
DATABASE_URL=sqlite:///./news.db
PORT=8000
```

## Development
- Add new sources in the backend under `app/`.
- Update frontend API base URL in `frontend/src/lib/api.ts` if backend runs on a different host/port.

## License
MIT. See LICENSE.
