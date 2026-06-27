from __future__ import annotations

import csv
import gzip
import html.parser
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.services.rag_service import RAGService


BASE_URL = "https://physionet.org/files/mimic-iv-demo/2.2/"
TARGET_DIR = ROOT / "data" / "mimic-iv-demo" / "2.2"
SOURCE_TYPE = "mimic_iv_demo_approved_public_dataset"
CURATED_FILES = [
    "README.txt",
    "LICENSE.txt",
    "demo_subject_id.csv",
    "hosp/admissions.csv.gz",
    "hosp/patients.csv.gz",
    "hosp/diagnoses_icd.csv.gz",
    "hosp/procedures_icd.csv.gz",
    "hosp/d_icd_diagnoses.csv.gz",
    "hosp/d_icd_procedures.csv.gz",
    "hosp/d_labitems.csv.gz",
    "hosp/labevents.csv.gz",
    "hosp/microbiologyevents.csv.gz",
    "hosp/omr.csv.gz",
    "hosp/prescriptions.csv.gz",
    "icu/icustays.csv.gz",
    "icu/d_items.csv.gz",
    "icu/chartevents.csv.gz",
    "icu/procedureevents.csv.gz",
]


class LinkParser(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        for key, value in attrs:
            if key == "href" and value:
                self.links.append(value)


def fetch_links(url: str) -> list[str]:
    with urllib.request.urlopen(url, timeout=60) as response:
        parser = LinkParser()
        parser.feed(response.read().decode("utf-8", errors="ignore"))
    return [link for link in parser.links if link not in {"../", "./"}]


def download_file(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size > 0:
        return
    part = destination.with_suffix(destination.suffix + ".part")
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=180) as response, part.open("wb") as handle:
                while True:
                    chunk = response.read(1024 * 256)
                    if not chunk:
                        break
                    handle.write(chunk)
            part.replace(destination)
            return
        except Exception:
            if part.exists():
                part.unlink()
            if attempt >= 3:
                raise
            time.sleep(2 * (attempt + 1))


def download_dataset(full: bool = False) -> list[Path]:
    downloaded: list[Path] = []
    if not full:
        for relative in CURATED_FILES:
            destination = TARGET_DIR / relative
            download_file(BASE_URL + relative, destination)
            downloaded.append(destination)
        return downloaded
    for link in fetch_links(BASE_URL):
        if link.endswith("/"):
            section = link.strip("/")
            for child in fetch_links(BASE_URL + link):
                if child.endswith("/"):
                    continue
                destination = TARGET_DIR / section / child
                download_file(BASE_URL + link + child, destination)
                downloaded.append(destination)
        else:
            destination = TARGET_DIR / link
            download_file(BASE_URL + link, destination)
            downloaded.append(destination)
    return downloaded


def open_csv(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="replace", newline="")
    return path.open("r", encoding="utf-8", errors="replace", newline="")


def read_rows(path: Path, max_rows: int | None = None) -> tuple[list[str], list[dict[str, str]], int]:
    rows: list[dict[str, str]] = []
    count = 0
    with open_csv(path) as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        for row in reader:
            count += 1
            if max_rows is None or len(rows) < max_rows:
                rows.append(row)
    return fields, rows, count


def top_values(rows: list[dict[str, str]], columns: list[str], limit: int = 8) -> list[str]:
    snippets: list[str] = []
    for column in columns:
        counter = Counter(row.get(column, "").strip() for row in rows if row.get(column, "").strip())
        if counter:
            values = ", ".join(f"{value} ({count})" for value, count in counter.most_common(limit))
            snippets.append(f"{column}: {values}")
    return snippets


def build_dictionary_maps() -> tuple[dict[str, str], dict[str, str], dict[str, str], dict[str, str]]:
    diagnoses: dict[str, str] = {}
    procedures: dict[str, str] = {}
    labs: dict[str, str] = {}
    items: dict[str, str] = {}
    dictionary_specs = [
        (TARGET_DIR / "hosp" / "d_icd_diagnoses.csv.gz", diagnoses, "icd_code", "long_title"),
        (TARGET_DIR / "hosp" / "d_icd_procedures.csv.gz", procedures, "icd_code", "long_title"),
        (TARGET_DIR / "hosp" / "d_labitems.csv.gz", labs, "itemid", "label"),
        (TARGET_DIR / "icu" / "d_items.csv.gz", items, "itemid", "label"),
    ]
    for path, mapping, key_name, label_name in dictionary_specs:
        if not path.exists():
            continue
        _, rows, _ = read_rows(path)
        for row in rows:
            key = row.get(key_name, "").strip()
            label = row.get(label_name, "").strip()
            if key and label:
                mapping[key] = label
    return diagnoses, procedures, labs, items


def summarize_table(path: Path, dictionaries: tuple[dict[str, str], dict[str, str], dict[str, str], dict[str, str]]) -> str | None:
    if path.suffixes[-2:] != [".csv", ".gz"] and path.suffix != ".csv":
        if path.name.lower().endswith(".txt"):
            text = path.read_text(encoding="utf-8", errors="replace")
            return f"Source file {path.relative_to(TARGET_DIR)} from MIMIC-IV demo 2.2.\n{text[:4000]}"
        return None

    fields, sample_rows, row_count = read_rows(path, max_rows=5000)
    relative = path.relative_to(TARGET_DIR).as_posix()
    table_name = path.name.replace(".csv.gz", "").replace(".csv", "")
    diagnoses, procedures, labs, items = dictionaries

    lines = [
        f"MIMIC-IV Clinical Database Demo version 2.2 table summary for {relative}.",
        "This is deidentified public demo data from PhysioNet for RAG education and workflow demonstration.",
        "Do not use this dataset to diagnose or prescribe for the current patient.",
        f"Rows: {row_count}. Columns: {', '.join(fields)}.",
    ]

    categorical_columns = [
        column
        for column in fields
        if column.lower()
        in {
            "admission_type",
            "admission_location",
            "discharge_location",
            "insurance",
            "language",
            "marital_status",
            "race",
            "gender",
            "eventtype",
            "careunit",
            "curr_service",
            "drug",
            "route",
            "spec_type_desc",
            "test_name",
            "org_name",
            "interpretation",
            "category",
        }
    ]
    lines.extend(top_values(sample_rows, categorical_columns))

    if table_name == "diagnoses_icd":
        code_counter = Counter(row.get("icd_code", "").strip() for row in sample_rows if row.get("icd_code", "").strip())
        concept_lines = [f"{code}: {diagnoses.get(code, 'Unknown diagnosis title')} ({count})" for code, count in code_counter.most_common(25)]
        lines.append("Common diagnosis concepts in this demo subset: " + "; ".join(concept_lines))
    elif table_name == "procedures_icd":
        code_counter = Counter(row.get("icd_code", "").strip() for row in sample_rows if row.get("icd_code", "").strip())
        concept_lines = [f"{code}: {procedures.get(code, 'Unknown procedure title')} ({count})" for code, count in code_counter.most_common(25)]
        lines.append("Common procedure concepts in this demo subset: " + "; ".join(concept_lines))
    elif table_name == "labevents":
        item_counter = Counter(row.get("itemid", "").strip() for row in sample_rows if row.get("itemid", "").strip())
        concept_lines = [f"{item}: {labs.get(item, 'Unknown lab item')} ({count})" for item, count in item_counter.most_common(30)]
        lines.append("Common lab event concepts in this demo subset: " + "; ".join(concept_lines))
    elif table_name == "chartevents":
        item_counter = Counter(row.get("itemid", "").strip() for row in sample_rows if row.get("itemid", "").strip())
        concept_lines = [f"{item}: {items.get(item, 'Unknown chart item')} ({count})" for item, count in item_counter.most_common(35)]
        lines.append("Common ICU chart concepts in this demo subset: " + "; ".join(concept_lines))
    elif table_name in {"d_icd_diagnoses", "d_icd_procedures", "d_labitems", "d_items"}:
        label_column = "long_title" if "long_title" in fields else "label"
        labels = [row.get(label_column, "").strip() for row in sample_rows if row.get(label_column, "").strip()]
        lines.append("Dictionary labels available for concept lookup: " + "; ".join(labels[:80]))

    return "\n".join(line for line in lines if line)


def existing_dataset_files() -> list[Path]:
    if not TARGET_DIR.exists():
        return []
    return [
        path
        for path in TARGET_DIR.rglob("*")
        if path.is_file() and not path.name.endswith(".part")
    ]


def ingest(full: bool = False, no_download: bool = False) -> dict:
    downloaded = existing_dataset_files() if no_download else download_dataset(full=full)
    dictionaries = build_dictionary_maps()
    rag = RAGService()
    indexed: list[dict] = []
    for path in sorted(downloaded):
        summary = summarize_table(path, dictionaries)
        if not summary:
            continue
        result = rag.index_document(
            title=f"MIMIC-IV Demo 2.2 - {path.relative_to(TARGET_DIR).as_posix()}",
            content=summary,
            source_type=SOURCE_TYPE,
            user_id=None,
            filename=str(path.relative_to(ROOT)),
        )
        indexed.append({"file": str(path.relative_to(ROOT)), **result})
    return {
        "downloaded_files": len(downloaded),
        "indexed_documents": len(indexed),
        "indexed_chunks": sum(item["chunk_count"] for item in indexed),
        "target_dir": str(TARGET_DIR),
        "items": indexed,
    }


if __name__ == "__main__":
    result = ingest(full="--all" in sys.argv, no_download="--no-download" in sys.argv)
    print(result)
