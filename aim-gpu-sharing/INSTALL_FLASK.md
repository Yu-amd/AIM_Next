# Installing Flask for Web Application

## Quick Install

```bash
pip3 install flask requests --break-system-packages --ignore-installed blinker
```

## Why `--ignore-installed blinker`?

On Debian/Ubuntu systems, `blinker` may be installed as a system package. The `--ignore-installed` flag allows pip to install a newer version without conflicts.

## Verify Installation

```bash
python3 -c "import flask; print('Flask installed successfully')"
python3 examples/web/web_app.py --help
```

## Alternative: Virtual Environment

If you prefer using a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
pip install flask requests
```

Then run the web app:
```bash
python3 examples/web/web_app.py --endpoint http://localhost:8000/v1
```
