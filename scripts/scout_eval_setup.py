"""Prepare a Scout checkout for a Dyno eval run (used by .github/workflows/eval.yml).

Run it with Scout's Python, since it imports Scout's own corpus code:

    scout-venv/bin/python scripts/scout_eval_setup.py SCOUT_DIR OUT_DIR

It writes, without touching the Scout checkout:
- OUT_DIR/config.eval.yaml: Scout's config.yaml with
  - the per-user job limit raised, since every case of a run comes from one user and
    50 cases x k would hit 10 jobs an hour;
  - trajectory fields kept up to 20,000 characters (Scout's default is 4,000), so a
    fetched page (fetch_url returns at most 20,000) reaches Dyno whole and the
    hallucination judge sees the passages Scout's own verifier saw.
- OUT_DIR/corpus/*.pdf: Scout's eval corpus (eval/corpus/*.txt) as PDFs, made by
  Scout's own load_corpus, for Dyno's Scout adapter to upload (SCOUT_CORPUS_DIR).
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

JOBS_PER_HOUR = 1000
FIELD_CHARS = 20_000


def main(scout_dir: Path, out_dir: Path) -> None:
    from scout.eval.corpus import load_corpus

    out_dir.mkdir(parents=True, exist_ok=True)
    config = yaml.safe_load((scout_dir / "config.yaml").read_text(encoding="utf-8"))
    config["jobs"]["max_per_hour_per_user"] = JOBS_PER_HOUR
    config["telemetry"]["max_field_chars"] = FIELD_CHARS
    (out_dir / "config.eval.yaml").write_text(yaml.safe_dump(config, sort_keys=False))

    corpus = out_dir / "corpus"
    corpus.mkdir(exist_ok=True)
    docs = load_corpus(scout_dir / "eval" / "corpus")
    for name, pdf in docs:
        (corpus / name).write_bytes(pdf)
    print(f"config: {out_dir / 'config.eval.yaml'}; corpus: {len(docs)} PDFs in {corpus}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(Path(sys.argv[1]), Path(sys.argv[2]))
