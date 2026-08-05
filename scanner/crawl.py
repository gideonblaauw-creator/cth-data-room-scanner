"""
scanner/crawl.py
Crawls a Google Drive folder recursively and returns a structured tree.

Called by Claude Code in-session — does NOT use the Drive REST API directly.
Instead, it produces a JSON structure that Claude reads via the MCP tool calls
embedded in the /scan slash command.

NOTE: This file is a reference scaffold. In a Claude Code session, the actual
MCP tool calls (Google Drive:search_files, Google Drive:read_file_content) are
made by Claude directly, not by running this Python script. This file documents
the data contract so Claude knows what shape the crawl output should take.
"""

DRIVE_TREE_SCHEMA = {
    "folder_id": "string",
    "folder_name": "string",
    "crawled_at": "ISO datetime",
    "total_files": "int",
    "total_folders": "int",
    "empty_folders": ["list of folder names that returned no files"],
    "items": [
        {
            "id": "string",
            "name": "string",
            "type": "folder | document | spreadsheet | presentation | pdf | other",
            "size_bytes": "int | null",
            "content_snippet": "string (first 4000 chars of readable content) | null",
            "children": ["...recursive same schema for folders"],
        }
    ],
}

# Folders that signal specific data room pillars
PILLAR_FOLDER_SIGNALS = {
    "team": ["equipo", "team", "cv", "currículum", "founders", "advisors"],
    "financials": [
        "finanzas", "financials", "financial", "presupuesto", "budget", "proyecciones"
    ],
    "legal": ["legal", "contratos", "contracts", "ip", "patentes", "cap table"],
    "impact": ["impacto", "impact", "esg", "asg", "sostenibilidad"],
    "market": ["mercado", "market", "competencia", "competitors"],
    "traction": ["clientes", "clients", "pipeline", "ventas", "sales", "contratos"],
    "investor": ["inversores", "investors", "deck", "pitch", "one-pager"],
}

# Files to prioritize reading (read these first, limit context)
PRIORITY_FILE_KEYWORDS = [
    "one-pager", "onepager", "pitch", "deck", "inversores",
    "cv", "currículum", "resume", "equipo", "team",
    "cap table", "safe", "contrato", "contract",
    "financial", "finanzas", "proyección", "projection",
    "impacto", "impact", "cif", "validation",
    "pipeline", "clientes", "market",
]

MAX_CONTENT_CHARS_PER_FILE = 4000   # cap per file to manage context window
MAX_FILES_TO_READ_FULLY = 20        # read full content for top 20 files
