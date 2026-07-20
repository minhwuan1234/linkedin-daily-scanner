# LinkedIn Scanner Dashboard v2

Minimal dark dashboard focused only on profiles that were successfully scanned.

## Replace files

Copy these files into the existing `frontend/` directory:

- `index.html`
- `styles.css`
- `app.js`

Keep your existing `config.js` if it already contains the correct Supabase URL and publishable/anon key.

## Run

```powershell
cd C:\Users\Admin\linkedin-daily-scanner\frontend
python -m http.server 8080
```

Open:

```text
http://localhost:8080
```

Or, if the server is running from the repository root:

```text
http://localhost:8080/frontend/
```

## Data behavior

The dashboard:

- reads from `linkedin_profile_snapshots`
- only loads rows where `name` is not null
- takes the latest snapshot for each `source_id`
- does not display matching, errors, failed scans, or unscanned sources
- shows details in a side drawer
