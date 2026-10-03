# Alumni Digital Universe

A responsive alumni memory universe built with Flask + SQLAlchemy + SQLite.

## Run
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Open http://127.0.0.1:5000

For LAN testing on a phone, connect both devices to the same Wi-Fi and open:
`http://YOUR_WINDOWS_IP:5000`

Find the IP:
```powershell
ipconfig
```

## Demo
- Register an alumni account
- Login
- Edit your own profile
- Add university/career information
- Create personal highlights
- Upload memories
- Browse the Memory Wall and Alumni Galaxy

SQLite is used for development through SQLAlchemy. PostgreSQL can be configured later with `DATABASE_URL`.
