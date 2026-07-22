import csv
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree


TEXT_EXTENSIONS = {".txt", ".md", ".json", ".yaml", ".yml", ".csv"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def extract_text(path: Path) -> tuple[str, bool, str]:
    suffix = path.suffix.lower()
    try:
        if suffix in {".txt", ".md", ".json", ".yaml", ".yml"}:
            return path.read_text(encoding="utf-8", errors="ignore"), True, ""
        if suffix == ".csv":
            return extract_csv(path), True, ""
        if suffix == ".docx":
            return extract_docx(path), True, ""
        if suffix == ".xlsx":
            return extract_xlsx(path), True, ""
        if suffix in IMAGE_EXTENSIONS:
            return "", True, "image"
    except Exception as error:  # noqa: BLE001
        return "", False, str(error)
    return "", False, "This file was uploaded successfully, but text extraction is not fully supported yet."


def extract_csv(path: Path) -> str:
    rows: list[str] = []
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
        reader = csv.reader(handle)
        for index, row in enumerate(reader):
            if index >= 500:
                rows.append("[truncated]")
                break
            rows.append(" | ".join(row))
    return "\n".join(rows)


def extract_docx(path: Path) -> str:
    namespaces = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    chunks: list[str] = []
    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    for paragraph in root.findall(".//w:p", namespaces):
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", namespaces)).strip()
        if text:
            chunks.append(text)
    return "\n".join(chunks)


def extract_xlsx(path: Path) -> str:
    namespaces = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    rows: list[str] = []
    with zipfile.ZipFile(path) as archive:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in root.findall(".//a:si", namespaces):
                shared_strings.append("".join(node.text or "" for node in item.findall(".//a:t", namespaces)))
        sheet_names = [name for name in archive.namelist() if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")]
        for sheet_name in sheet_names[:5]:
            root = ElementTree.fromstring(archive.read(sheet_name))
            rows.append(f"[{sheet_name}]")
            for row_index, row in enumerate(root.findall(".//a:row", namespaces)):
                if row_index >= 200:
                    rows.append("[truncated]")
                    break
                values: list[str] = []
                for cell in row.findall("a:c", namespaces):
                    value_node = cell.find("a:v", namespaces)
                    value = value_node.text if value_node is not None else ""
                    if cell.attrib.get("t") == "s" and value.isdigit():
                        value = shared_strings[int(value)] if int(value) < len(shared_strings) else value
                    values.append(value)
                if values:
                    rows.append(" | ".join(values))
    return "\n".join(rows)


def json_preview(value: object) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False)[:12000]
