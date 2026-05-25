# Usage

`odoo-studio-extractor` is a single-purpose CLI: it connects to an Odoo
instance read-only and exports Studio customizations.

## Install

```bash
git clone https://github.com/your-org/odoo-studio-extractor.git
cd odoo-studio-extractor
python -m venv .venv
. .venv/Scripts/activate    # PowerShell on Windows
pip install -e .
# Optional, for `.env` support:
pip install -e ".[dotenv]"
```

## Configure

Copy `.env.example` to `.env` and fill in the four variables, **or** export
them directly in your shell:

```powershell
$env:ODOO_URL = "https://your-odoo-host.example.com"
$env:ODOO_DB = "your_database_name"
$env:ODOO_USERNAME = "readonly_audit_user"
$env:ODOO_PASSWORD = "..."
```

```bash
export ODOO_URL=https://your-odoo-host.example.com
export ODOO_DB=your_database_name
export ODOO_USERNAME=readonly_audit_user
export ODOO_PASSWORD=...
```

> Use a **read-only** Odoo user. The CLI itself enforces read-only access on
> the client side, but a read-only DB user is your best second line of defense.

## Run an audit

```bash
odoo-studio-extractor audit --output outputs/studio_audit
```

You can override the XML-RPC timeout:

```bash
odoo-studio-extractor audit --output outputs/studio_audit --timeout 60
```

## Outputs

After a successful run:

- `outputs/studio_audit/studio_report.md` — the human-readable Markdown report.
- `outputs/studio_audit/studio_data.json` — the full raw dataset.

A short summary is printed to the terminal, including per-category counts and
the file paths.

## Exit codes

| Code | Meaning                               |
|------|---------------------------------------|
| 0    | Success                               |
| 2    | Configuration error (missing env var) |
| 3    | Authentication failed                 |
| 4    | Network / connection error            |
| 5    | Generic Odoo client error             |

## Programmatic use

You can also use the package as a library:

```python
from odoo_studio_extractor.client import OdooClient
from odoo_studio_extractor.config import load_config
from odoo_studio_extractor.extractors import extract_models, extract_fields

config = load_config()
client = OdooClient(config)
client.authenticate()

models = extract_models(client)
fields = extract_fields(client, extra_models=[m["model"] for m in models])
```

The `OdooClient` class only exposes read-only methods: any attempt to use
`create`, `write`, `unlink`, etc. will raise `UnsafeOperationError`.
