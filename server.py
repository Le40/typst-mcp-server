from mcp.server import MCPServer

import tools
from config import CUSTOM_EXPORTER

mcp = MCPServer("Typst CV")


@mcp.tool()
def list_files() -> list[str]:
    """List files available in the Typst CV project."""
    return tools.list_files()


@mcp.tool()
def read_file(path: str) -> str:
    """Read a permitted project file using its relative path."""
    return tools.read_file(path)

@mcp.tool()
def create_file(path: str, content: str) -> dict:
    """Create a new Typst CV application without overwriting existing files."""
    return tools.create_file(path, content)

@mcp.tool()
def compile_typst(source: str, output: str) -> dict:
    """Compile a permitted Typst file to PDF in the configured output directory."""
    return tools.compile_typst(source, output)

if CUSTOM_EXPORTER is not None:
    @mcp.tool()
    def export_document(
        target: str,
        options: dict[str, str] | None = None
    ) -> dict:
        """Export documents using the configured project exporter."""
        return tools.export_document(target, options)

    @mcp.tool()
    def get_export_info() -> dict:
        """Describe the configured exporter, its target and available options."""
        return tools.get_export_info()


if __name__ == "__main__":
    mcp.run()