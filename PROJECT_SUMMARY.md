# Snyk API&Web (SAW) MCP Server - Project Summary

## Project Overview

**Snyk API&Web MCP Server** is a comprehensive Model Context Protocol (MCP) server that provides AI assistants with full access to the Snyk API&Web security testing platform API.

## Project Information

- **Name**: Snyk API&Web MCP Server (SAW)
- **Version**: 1.0.0
- **Type**: MCP Server for Snyk API&Web API
- **Language**: Python (FastMCP 2.0)
- **License**: MIT

## What It Does

This MCP server enables AI assistants (like Cursor, Devon, Windsurf) to interact with the Snyk API&Web security testing platform through natural language. Users can:

- Manage security scan targets
- Start and monitor security scans
- View and manage security findings
- Generate security reports
- Manage teams and users
- Configure authentication (form login, login sequences, 2FA, logout detection)

## Features Implemented

### API Coverage

The server exposes the most-used Snyk API&Web functionality as MCP tools:

- **Targets** - Create and manage scan targets (web and API)  
- **Scans** - Start, stop, monitor scans  
- **Findings** - View and manage vulnerabilities  
- **Login Sequences** - Record and manage login sequences  
- **Authentication** - Configure form login, sequence login, 2FA  
- **Logout Detection** - Configure logout detectors and session checks  
- **Extra Hosts** - Configure additional hosts  
- **Labels** - Create labels for organization  
- **Teams** - List and view teams  
- **Users** - View user details  
- **Scanning Agents** - List and view scanning agents  
- **Target Settings** - Configure scan profiles  
- **Reports** - Generate PDF and HTML reports  

## Project Structure

```
SnykAPIWeb/
├── snyk_apiweb/                  # Python source code
│   ├── __init__.py
│   ├── config.py                # Configuration loader
│   ├── probely_client.py        # API client
│   ├── server.py                # Main MCP server
│   └── tools.py                 # MCP tool implementations
│
├── config/                       # Configuration files
│   ├── config.yaml              # Server config (API key here)
│   └── project_rules.yaml       # Project rules
│
├── .cursor/                      # Cursor IDE rules
│   └── rules/
│       └── saw_rules.mdc        # SAW integration rules
│
├── examples/                     # Configuration examples
│   ├── cursor-config.json       # Cursor IDE config
│   └── EXAMPLES.md              # Usage examples
│
├── scripts/                      # Utility scripts
│   └── package.sh               # Packaging script
│
├── dist/                         # Distribution package
│   └── SnykAPIWeb.tgz           # Installable package
│
├── requirements.txt              # Python dependencies
├── README.md                     # Project documentation
├── INSTALL.md                    # Installation guide
├── PROJECT_SUMMARY.md            # This file
└── LICENSE                       # MIT license
```

## Technology Stack

- **Language**: Python 3.10+
- **MCP Framework**: FastMCP 2.0
- **HTTP Client**: requests with tenacity for retries

## Development Setup

### Prerequisites
- Python 3.10 or higher
- pip

### Build from Source

```bash
# Clone or navigate to the project
cd SnykAPIWeb

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the server
./venv/bin/python -m snyk_apiweb.server
```

## Configuration

### API Key Setup

The server requires a Snyk API&Web API key in `config/config.yaml`:

```yaml
saw:
  base_url: "https://api.probely.com"
  api_key: "your-api-key-here"
```

Or use the environment variable `MCP_SAW_CONFIG_PATH` to point to your config file.

## IDE Integration

### Supported IDEs

- **Cursor** - Full support with example config
- **Devon** - Full support with example config
- **Windsurf** - Compatible
- **Any MCP-compatible IDE** - Standard protocol

### Configuration Examples

Located in `examples/` directory:
- `cursor-config.json` - Use in Cursor MCP settings
- `EXAMPLES.md` - Usage patterns and queries

## API Client Implementation

The API client (`snyk_apiweb/probely_client.py`) implements:

### Core Methods
- Full REST API coverage
- Automatic authentication via JWT
- Error handling and retries
- Type-safe responses
- Pagination support

### API Base URL
- Default: `https://api.probely.com`
- Configurable via config file

### Authentication
- JWT token in Authorization header
- Format: `Authorization: JWT <api-key>`

## MCP Server Implementation

The MCP server (`snyk_apiweb/tools.py`) implements:

### MCP Protocol Features
- Tool listing
- Tool execution
- Proper error handling
- JSON response formatting
- STDIO transport

### Tool Categories
- 1 User tool (read-only)
- 2 Team tools (read-only)
- 1 Label tool
- 7 Target Management tools
- 5 Login Sequence tools
- 7 Authentication & Logout tools
- 5 Extra Host tools
- 5 Scan tools
- 4 Finding tools
- 2 Target Settings tools
- 3 Report tools
- 2 Scanning Agent tools
- 2 API Target Creation tools

**Total: 46 tools**

## Security Considerations

### API Key Security
- Never commit API keys to git
- Use environment variables or config files
- Rotate keys regularly
- Minimum required permissions

### HTTPS
- All API calls use HTTPS
- TLS certificate verification

## Deployment

### Global Installation

```bash
# Run from project directory
./venv/bin/python -m snyk_apiweb.server
```

### Package Distribution

```bash
bash scripts/package.sh
```

Creates: `dist/SnykAPIWeb.tgz`

## Troubleshooting

Common issues and solutions documented in:
- `INSTALL.md` - Installation issues
- `README.md` - General troubleshooting

## Future Enhancements

Potential improvements:
- [ ] Add caching for frequently accessed data
- [ ] Implement webhook support
- [ ] Add batch operations
- [ ] Enhanced error messages
- [ ] Rate limit handling

## License

MIT License - see LICENSE file

## Support

- **Snyk API&Web API**: https://developers.probely.com/api/reference
- **MCP Protocol**: https://modelcontextprotocol.io

## Project Status

- **Complete** - All features implemented  
- **Tested** - Manual testing completed  
- **Documented** - Full documentation provided  
- **Packaged** - Distribution ready  
- **Ready for use** - Production-ready  

## Quick Links

- **Main Docs**: `README.md`
- **Installation**: `INSTALL.md`
- **Examples**: `examples/EXAMPLES.md`

---

**Project completed and ready for distribution!**
