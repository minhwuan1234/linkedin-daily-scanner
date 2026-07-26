# Railway + Lark webhook — Step 2

Add these files to the root of `linkedin-daily-scanner`:

- `backend/__init__.py`
- `backend/main.py`
- `railway.json`
- Replace `requirements.txt` with the included version.

Then run:

```bash
git add backend railway.json requirements.txt
git commit -m "Add Railway Lark webhook backend"
git push origin main
```

Railway start command is:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

Health endpoint:

```text
https://YOUR-RAILWAY-DOMAIN/health
```

Lark callback endpoint:

```text
https://YOUR-RAILWAY-DOMAIN/webhooks/lark/events
```

This step only receives/logs Lark events. It does not modify the existing Google Sheet, daily scan, Playwright, or Supabase data flow.
