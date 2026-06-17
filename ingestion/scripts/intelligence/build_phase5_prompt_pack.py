from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from traceready_ingestion.intelligence.phase05_ai_assisted_extraction import build_phase5_prompt_specs, render_prompt, select_phase5_source_chunks


def main() -> None:
    parser = argparse.ArgumentParser(description="Build TraceReady Phase 5 structured-output prompt pack.")
    parser.add_argument("--chunks-file", default="../data/regulatory/registry/source-chunks.json")
    parser.add_argument("--output-dir", default="../data/regulatory/intelligence/phase5/prompts")
    args = parser.parse_args()

    chunks = json.loads(Path(args.chunks_file).read_text(encoding="utf-8"))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    specs = build_phase5_prompt_specs()
    prompt_pack = []
    for spec in specs:
        relevant_chunks = select_phase5_source_chunks(spec.collection, chunks)
        prompt_text = render_prompt(spec, relevant_chunks)
        prompt_file = output_dir / f"{spec.prompt_id}.md"
        prompt_file.write_text(prompt_text, encoding="utf-8")
        prompt_pack.append(
            {
                **spec.model_dump(mode="json"),
                "promptFile": str(prompt_file),
                "sourceChunkIds": [chunk["chunk_id"] for chunk in relevant_chunks],
            }
        )

    pack_path = output_dir / "phase5-prompt-pack.json"
    pack_path.write_text(json.dumps({"prompts": prompt_pack}, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "promptCount": len(prompt_pack),
                "outputDir": str(output_dir),
                "promptPack": str(pack_path),
            },
            indent=2,
        )
    )

if __name__ == "__main__":
    main()
