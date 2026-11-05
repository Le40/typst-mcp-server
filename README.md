# Typst MCP Server

A small Python MCP server that allows AI agents to work with existing [Typst](https://typst.app/) projects.

I built this project while learning about MCP (Model Context Protocol) and how AI agents can interact with external tools.

The initial use case was my own Typst-based CV and cover letter system. I wanted to let an AI agent explore the existing project, understand its structure, create tailored documents, and export PDFs without directly modifying the shared templates and content.

After getting that working with OpenAI Codex, I made the server configurable so it could also be used with other Typst projects.

## How it works

The server exposes a few tools through MCP:

| Tool | Purpose |
|---|---|
| `list_files` | List files available to the agent |
| `read_file` | Read a permitted project file |
| `create_file` | Create a new Typst file without overwriting existing files |
| `compile_typst` | Compile a Typst document to PDF |
| `get_export_info` | Describe the configured custom exporter |
| `export_document` | Run a project's custom export script |

The last two tools are optional.

The AI agent decides which files to inspect and how to use the project's existing templates. The MCP server handles file access, validation and execution of the requested operations.

### Configuration and permissions

Each project is configured through a local TOML file. It defines the project location, permitted read and create paths, and output directory.

For example:

```toml
project_root = "../my-typst-project"
output_dir = "output"

[permissions]
read = ["main.typ", "templates/", "content/"]
create = ["documents/"]
```

The server checks requested paths against these permissions. New files are created using Python's exclusive creation mode, so existing files cannot be overwritten through the creation tool.

Projects can also define a custom exporter for more advanced workflows, such as generating multiple documents or language versions. The exporter is configured in TOML and returns generated file paths through a simple JSON output convention.

See `config.example.toml` for the available settings.

## Running locally

Requirements: Python 3.14+, Typst CLI, and an MCP-compatible client.

Clone the repository and install dependencies:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Copy `config.example.toml` to `config.local.toml` and update the paths for your Typst project.

In your MCP client, add a local STDIO server using your virtual environment's Python executable, with `server.py` as its argument.

I tested the integration with the Codex extension in VS Code on Windows.

## Tests

Basic permission tests are implemented with pytest:

```powershell
python -m pytest -v
```

They cover allowed and forbidden file access, path traversal, create-only behavior and overwrite prevention. A symlink escape test is also included, although it may be skipped on systems where creating symlinks is unavailable.

## Limitations

This is a local proof-of-concept project, not a complete security sandbox.

The permission checks restrict operations performed through the MCP tools. They don't control other filesystem tools an AI client might have access to. Custom export scripts also run with the permissions of the local process and should be trusted.

The server was developed and tested primarily with my own Typst project, which is not included in this repository.
