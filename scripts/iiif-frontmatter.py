#!/usr/bin/env python3
"""Add IIIF manifest support to flohmarktfunde posts.

For every page bundle in content/post/ that contains images, this script adds
to both the German (index.md) and English (index.en.md) content files:

- ``outputs: [html, iiif-manifest]`` so Hugo renders a IIIF Presentation manifest
- ``resources:`` entries for the bundle images, ordered like the ``figure``
  shortcodes in the body (the manifest partial only renders declared resources)
- ``title:`` derived from the '**Objekt:**' / '**Object:**' body line when the
  file has no title, so manifest labels aren't empty

Bundles without images are skipped (they can't produce valid manifests, the
theme's thumbnail partial requires at least one declared resource).

The script is idempotent: files that already carry the wanted front matter are
left untouched. Existing ``resources`` blocks are never modified.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "content" / "post"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".jxl", ".tif", ".tiff"}

OBJECT_RE = {
    "de": re.compile(r"^\*\*Objekt:\*\*[ \t]*(.*)$", re.MULTILINE),
    "en": re.compile(r"^\*\*Object:\*\*[ \t]*(.*)$", re.MULTILINE),
}
FIGURE_RE = re.compile(
    r"{{<?\s*figure\b[^>]*?\bsrc\s*=\s*[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)

warnings = []


def warn(message):
    warnings.append(message)
    print(f"WARN: {message}")


def split_front_matter(text):
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return None, text
    return match.group(1), text[match.end():]


def has_key(front_matter, key):
    return re.search(rf"^{key}:", front_matter, re.MULTILINE) is not None


def outputs_include_manifest(front_matter):
    match = re.search(r"^outputs:\n((?:[ \t]*-.*\n?)+)", front_matter, re.MULTILINE)
    if not match:
        return False
    return "iiif-manifest" in match.group(1)


def yaml_quote(value):
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def derive_title(body, language, folder):
    label = "Objekt" if language == "de" else "Object"
    match = OBJECT_RE[language].search(body)
    if match:
        value = re.sub(r"\s*(<br\s*/?>|\\)+\s*$", "", match.group(1)).strip()
        if value:
            return value
        warn(f"{folder}: empty '**{label}:**' line, using folder name as title")
    else:
        warn(f"{folder}: no '**{label}:**' line, using folder name as title")
    return folder.replace("-", " ").title()


def ordered_resources(images, body, folder):
    ordered = []
    for src in FIGURE_RE.findall(body):
        name = Path(src).name
        if name in images and name not in ordered:
            ordered.append(name)
        elif name not in images:
            warn(f"{folder}: figure references '{src}' but the file is not in the bundle")
    missing = sorted(set(images) - set(ordered))
    for name in missing:
        warn(f"{folder}: image '{name}' is not referenced by a figure shortcode, appending it")
        ordered.append(name)
    return ordered


def process_file(path):
    language = "en" if path.name.endswith(".en.md") else "de"
    folder = path.parent.name
    text = path.read_text(encoding="utf-8")
    front_matter, body = split_front_matter(text)
    if front_matter is None:
        warn(f"{path}: no front matter found, skipping")
        return "skipped"

    images = sorted(
        entry.name for entry in path.parent.iterdir()
        if entry.is_file() and entry.suffix.lower() in IMAGE_SUFFIXES
    )
    if not images:
        return "no-images"

    needs = []
    if not has_key(front_matter, "title"):
        needs.append("title")
    if not has_key(front_matter, "outputs") or not outputs_include_manifest(front_matter):
        needs.append("outputs")
    if not has_key(front_matter, "resources"):
        needs.append("resources")
    if not needs:
        return "unchanged"

    additions = []
    if "title" in needs:
        additions.append(f"title: {yaml_quote(derive_title(body, language, folder))}")
    if "outputs" in needs:
        if has_key(front_matter, "outputs"):
            additions.append("outputs:\n- iiif-manifest")
        else:
            additions.append("outputs:\n- html\n- iiif-manifest")
    if "resources" in needs:
        entries = "\n".join(f"- src: {name}" for name in ordered_resources(images, body, folder))
        additions.append(f"resources:\n{entries}")

    new_front_matter = front_matter
    if additions and additions[0].startswith("title:"):
        new_front_matter = additions[0] + "\n" + new_front_matter
        additions = additions[1:]
    if additions:
        if not new_front_matter.endswith("\n"):
            new_front_matter += "\n"
        new_front_matter += "\n".join(additions) + "\n"

    path.write_text("---\n" + new_front_matter + "---\n" + body, encoding="utf-8")
    return "updated"


def main():
    if not POSTS.is_dir():
        print(f"ERROR: {POSTS} not found", file=sys.stderr)
        return 1
    counts = {"updated": 0, "unchanged": 0, "no-images": 0, "skipped": 0}
    for bundle in sorted(POSTS.iterdir()):
        if not bundle.is_dir():
            continue
        for name in ("index.md", "index.en.md"):
            path = bundle / name
            if path.is_file():
                counts[process_file(path)] += 1
    print(
        "Done: "
        + ", ".join(f"{key}: {value}" for key, value in counts.items())
        + f", warnings: {len(warnings)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
