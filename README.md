# LinkedIn Scanner Dashboard

1. Mở `config.js`, điền Supabase URL và publishable/anon key.
2. Chạy `supabase-read-policy.sql` trong Supabase SQL Editor.
3. Chạy local:

```powershell
cd linkedin-dashboard
python -m http.server 8080
```

4. Mở `http://localhost:8080`.

Chỉ dùng publishable/anon key trong frontend. Không dùng secret/service-role key.
