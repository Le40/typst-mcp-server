import json
import re
import subprocess
from pathlib import Path

from config import CREATE_RULES, CUSTOM_EXPORTER, OUTPUT_DIR, PROJECT_ROOT, READ_RULES


def compile_typst(source: str, output: str) -> dict:
    try:
        # Validate source using read permissions
        source_path = get_permitted_file(source, READ_RULES)

        if not source_path.is_file() or source_path.suffix != ".typ":
            raise ValueError("Invalid Typst source")

        # Validate destination using output directory permissions
        output_folder = OUTPUT_DIR.relative_to(PROJECT_ROOT).as_posix() + "/"
        output_path = get_allowed_path(output, [output_folder])

        if output_path.suffix != ".pdf":
            raise ValueError("Output must be a PDF")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Compile using Typst
        result = subprocess.run(
            [
                "typst", "compile",
                "--root", str(PROJECT_ROOT),
                str(source_path),
                str(output_path)
            ],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            return {
                "success": False,
                "path": None,
                "error": result.stderr.strip() or "Typst compilation failed",
                "exit_code": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
            }

        return {
            "success": True,
            "path": str(output_path),
            "error": None,
        }


    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        return {"success": False,"path": None,"error": str(error),}
    

def list_project_files() -> list[str]:
    files = set()

    for location in READ_RULES:
        path = PROJECT_ROOT / location

        if location.endswith("/"):
            candidates = path.rglob("*") if path.is_dir() else []
        else:
            candidates = [path]

        for file in candidates:
            if not file.is_file():
                continue

            relative_path = file.relative_to(PROJECT_ROOT).as_posix()

            try:
                get_permitted_file(relative_path, READ_RULES)
                files.add(relative_path)
            except (ValueError, OSError):
                continue

    return sorted(files)


def read_file(path: str) -> str:
    target_path = get_permitted_file(path, READ_RULES)

    if not target_path.is_file():
        raise ValueError("File type not allowed")

    return target_path.read_text(encoding="utf-8")


def create_file(path: str, content: str) -> dict:
    try:
        target_path = get_permitted_file(path, CREATE_RULES)

        if not target_path.parent.is_dir():
            raise ValueError("Destination directory does not exist")

        with target_path.open("x", encoding="utf-8") as file:
            file.write(content)

        return {"success": True, "path": str(target_path)}

    except (ValueError, FileExistsError) as error:
        return {"success": False, "error": str(error)}


def get_allowed_path(path: str, allowed_paths: list[str]) -> Path:
    relative = Path(path)

    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Access denied")

    root = PROJECT_ROOT.resolve()
    target = (root / relative).resolve()

    if not target.is_relative_to(root):
        raise ValueError("Access denied")

    for entry in allowed_paths:
        allowed = (root / entry.rstrip("/")).resolve()

        if entry.endswith("/"):
            if target.is_relative_to(allowed):
                return target
        elif target == allowed:
            return target
        
    raise ValueError("Access denied")

def get_permitted_file(path: str, rules: dict) -> Path:
    # Check path permissions and prevent traversal
    file_path = get_allowed_path(path, list(rules))

    # Check file extension for the matching rule
    for location, extensions in rules.items():
        allowed_path = (PROJECT_ROOT / location).resolve()

        if location.endswith("/"):
            matches = file_path.is_relative_to(allowed_path)
        else:
            matches = file_path == allowed_path

        if matches and file_path.suffix.lower() in extensions:
            return file_path

    raise ValueError("File type not allowed")


def export_document(target: str, options: dict | None = None) -> dict:
    if CUSTOM_EXPORTER is None:
        return {"success": False, "error": "No custom exporter configured"}

    if not re.fullmatch(r"[A-Za-z0-9_-]+", target):
        return {"success": False, "error": "Invalid target"}

    options = options or {}
    available_options = CUSTOM_EXPORTER.get("options", {})

    if options.keys() - available_options.keys():
        return {"success": False, "error": "Unknown export option"}

    script = (PROJECT_ROOT / CUSTOM_EXPORTER["script"]).resolve()

    if not script.is_relative_to(PROJECT_ROOT) or not script.is_file():
        return {"success": False, "error": "Invalid exporter script"}

    command = [
        *CUSTOM_EXPORTER["command"],
        str(script),
        CUSTOM_EXPORTER["target_flag"],
        target
    ]

    for name, spec in available_options.items():
        value = options.get(name, spec.get("default"))

        if value is not None:
            if value not in spec["allowed"]:
                return {"success": False, "error": f"Invalid option: {name}"}

            command.extend([spec["flag"], str(value)])

    try:
        result = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=120
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"success": False, "error": str(error)}

    if result.returncode != 0:
        return {
            "success": False,
            "error": result.stderr.strip() or result.stdout.strip() or "Export failed",
            "exit_code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }

    result_line = next(
        (line.removeprefix("EXPORT_RESULT=")
         for line in result.stdout.splitlines()
         if line.startswith("EXPORT_RESULT=")),
        None
    )

    if result_line is None:
        return {
            "success": False,
            "error": "Exporter did not report generated files",
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }

    try:
        files = json.loads(result_line)["files"]
        if not isinstance(files, list) or not files:
            raise ValueError("Invalid export file list")

        output_root = OUTPUT_DIR.resolve()
        paths = []

        for file in files:
            path = Path(file)
            path = (path if path.is_absolute() else PROJECT_ROOT / path).resolve()

            if not path.is_relative_to(output_root) or not path.is_file():
                raise ValueError(f"Invalid exported file: {file}")

            paths.append(str(path))

    except (ValueError, KeyError, TypeError) as error:
        return {"success": False, "error": str(error)}

    return {"success": True, "files": paths, "error": None}


def get_export_info() -> dict:
    if CUSTOM_EXPORTER is None:
        return {"error": "No custom exporter configured"}

    return {
        "target": CUSTOM_EXPORTER.get("target_description", ""),
        "options": {
            name: {
                "description": spec.get("description", ""),
                "default": spec.get("default"),
                "allowed": spec["allowed"]
            }
            for name, spec in CUSTOM_EXPORTER.get("options", {}).items()
        }
    }