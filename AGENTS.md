# AGENTS.md — notes for running this repo in the Base44 sandbox

## Run it

```bash
docker compose -f docker-compose.base44.yml up -d --build
```

The site is then served on **host port 3000** (mapped to Flask's 5000). No external
credentials are needed: the database is a local MariaDB service.

## Non-obvious setup facts

- `app.py`/`database.py` read MySQL from the XAMPP defaults in `config.py`
  (`127.0.0.1:3306`, user `root`, empty password, database `pnru_sport`). To keep
  `config.py` untouched for the students' XAMPP workflow, the `web` service shares the
  `db` service's network namespace (`network_mode: service:db`), exactly like
  `.devcontainer/docker-compose.yml`. Consequence: Docker forbids `ports:` on such a
  service, so **the published `3000:5000` mapping lives on the `db` service**.
- Demo data is loaded by MariaDB's first-init hook from `pnru_sport_demo.sql` (same
  content as `python init_db.py --demo`). It only runs on an empty data volume.
  To reseed an existing volume:
  ```bash
  docker compose -f docker-compose.base44.yml exec -T db sh -c 'mariadb -uroot < /docker-entrypoint-initdb.d/pnru_sport_demo.sql'
  ```
- Demo accounts (also in README.md): admins `admin1` / `admin2` with `admin1234`;
  students `6512345678901`–`6512345678903` with `123456`. Login uses one field, so an
  admin types the username there.
- **Time-dependent demo data:** `app.py` runs `refresh_statuses()` on every request, so
  the September-2026 demo records are auto-converted with the real clock ("รอยืนยัน"
  that is past its 30-minute pickup window becomes "ยกเลิก", "กำลังยืม" past 16:00
  becomes "เกินกำหนด"). That is normal app behaviour, not a broken seed result. For the
  fixed scenarios in TESTING.md, set `FAKE_NOW` in `config.py` and restart the server.
- `TZ=Asia/Bangkok` is set in compose because booking hours (Mon–Fri 09:00–15:30) and
  deadlines are evaluated in Thai local time.
- Dev loop: the `web` service runs `flask --app app run --debug`, so the Werkzeug
  reloader restarts on `.py` edits (verified with `touch app.py`); Jinja templates are
  re-read on every request. `config.DEBUG` itself stays `False` (that flag only affects
  `python app.py`) — do not flip it in the repo.
- Because `config.SECRET_KEY` is empty, the session key is random per process: every
  reloader restart signs users out. Expected, documented behaviour.

## Verifying

- Health: `docker compose -f docker-compose.base44.yml ps` (both services report
  healthy; the `web` check fetches `/`, which needs a working DB connection).
- Quick end-to-end check with cookies:
  ```bash
  curl -s -c /tmp/j -b /tmp/j -d 'username=admin1&password=admin1234' \
       -o /dev/null -w '%{http_code} %{redirect_url}\n' http://localhost:3000/login
  curl -s -b /tmp/j http://localhost:3000/admin/pending | grep -c ยืนยันรับอุปกรณ์
  ```
- The repo's test suite is the manual checklist in TESTING.md (`test_models.py` needs
  `pytest`, which is not in `requirements.txt`).
- In the Base44 preview browser, cookies are not kept between checks (no replayed user
  session), so a signed-in page render is confirmed within a single check instead:
  `fetch('/login', {method:'POST', credentials:'same-origin', ...})` then
  `fetch('/admin/pending', {credentials:'same-origin'})` returns the admin HTML.
