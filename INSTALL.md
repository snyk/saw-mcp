# Install & Run Snyk API&Web (SAW) MCP Server

## 1) Extract
```bash
tar -xzvf SnykAPIWeb.tgz
cd SnykAPIWeb
```

## 2) Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 3) Configure
Edit `config/config.yaml` and set your Snyk API&Web API key.

## 4) Run MCP server
```bash
./venv/bin/python -m snyk_apiweb.server
```

## 5) Configure in Cursor (or other IDE)
- Command: `./venv/bin/python`
- Args: `-m`, `snyk_apiweb.server`
- Env: `MCP_SAW_CONFIG_PATH=./config/config.yaml`

Note: If your IDE does not resolve relative paths from the project root, use absolute paths (e.g., `/path/to/SnykAPIWeb/venv/bin/python`) and set `PYTHONPATH` to the project directory.
