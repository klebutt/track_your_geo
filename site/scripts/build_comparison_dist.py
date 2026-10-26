#!/usr/bin/env python3
"""Build a report dist in a subprocess (avoids importing cached site/build from wrong repo)."""

from __future__ import annotations

import argparse
import inspect
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument(
        "--bundles",
        type=str,
        default="{}",
        help='JSON map slug -> [md_path, pdf_path]',
    )
    parser.add_argument("--sample", action="store_true")
    args = parser.parse_args()

    repo = args.repo_root.resolve()
    sys.path.insert(0, str(repo / "apps" / "api"))
    sys.path.insert(0, str(repo / "site"))

    from build import build_report_page, build_sample_report, copy_public_files, load_config

    bundles: dict[str, list[str]] = json.loads(args.bundles)
    dist = args.dist.resolve()
    config = load_config()
    copy_public_files(dist, config)
    if args.sample:
        build_sample_report(dist, config)

    sig = inspect.signature(build_report_page)
    accepts_run = "run" in sig.parameters

    for slug, paths in bundles.items():
        md_path = Path(paths[0])
        pdf_path = Path(paths[1])
        kwargs = {
            "md_path": md_path,
            "pdf_path": pdf_path,
            "slug": slug,
            "dist": dist,
            "config": config,
        }
        if accepts_run:
            json_path = md_path.with_name(f"{md_path.stem}.run.json")
            if json_path.is_file():
                kwargs["run"] = json.loads(json_path.read_text(encoding="utf-8"))
        build_report_page(**kwargs)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
