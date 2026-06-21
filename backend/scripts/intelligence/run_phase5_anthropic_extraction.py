from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from typing import Any

from bellwether_backend.intelligence.phase05_ai_assisted_extraction import (
    build_phase5_prompt_specs,
    render_prompt,
    select_phase5_source_chunks,
    validate_ai_records,
)
from bellwether_backend.intelligence.anthropic_client import AnthropicJSONClient, AnthropicJSONParseError, AnthropicLLMConfig
from bellwether_backend.intelligence.citations import load_chunk_index


def main() -> None:
    parser = argparse.ArgumentParser(description="Run real Anthropic-backed Phase 5 extraction for Bellwether regulatory intelligence.")
    parser.add_argument("--chunks-file", default="../data/regulatory/registry/source-chunks.json")
    parser.add_argument("--output-dir", default="../data/regulatory/intelligence/phase5/anthropic-runs")
    parser.add_argument(
        "--collection",
        action="append",
        choices=["obligations", "exemption_rules", "tlc_rules"],
        help="Collection to run. Repeat for multiple. Defaults to all Phase 5 collections.",
    )
    parser.add_argument("--model", default=None, help="Override BELLWETHER_ANTHROPIC_MODEL for this run.")
    parser.add_argument("--conflict-model", default=None, help="Override BELLWETHER_ANTHROPIC_CONFLICT_MODEL for this run report.")
    parser.add_argument("--max-tokens", type=int, default=None, help="Override BELLWETHER_ANTHROPIC_MAX_TOKENS for this run.")
    parser.add_argument("--prompt-cache-ttl", choices=["1h"], default=None, help="Use Anthropic prompt cache TTL for this run. Omit for default ephemeral TTL.")
    parser.add_argument("--no-prompt-cache", action="store_true", help="Disable Anthropic prompt caching for this run.")
    args = parser.parse_args()

    run_id = datetime.now(UTC).strftime("phase5-anthropic-%Y%m%dT%H%M%SZ")
    output_dir = Path(args.output_dir) / run_id
    input_dir = output_dir / "input"
    raw_dir = output_dir / "raw"
    output_text_dir = output_dir / "output"
    validated_dir = output_dir / "validated"
    input_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)
    output_text_dir.mkdir(parents=True, exist_ok=True)
    validated_dir.mkdir(parents=True, exist_ok=True)

    chunks = json.loads(Path(args.chunks_file).read_text(encoding="utf-8"))
    chunk_index = load_chunk_index(Path(args.chunks_file))
    config = AnthropicLLMConfig.from_env()
    if args.model:
        config = AnthropicLLMConfig(
            api_key=config.api_key,
            model=args.model,
            conflict_model=args.conflict_model or config.conflict_model,
            max_tokens=args.max_tokens or config.max_tokens,
            temperature=config.temperature,
            prompt_cache_enabled=not args.no_prompt_cache,
            prompt_cache_ttl=args.prompt_cache_ttl or config.prompt_cache_ttl,
        )
    elif args.max_tokens or args.conflict_model or args.prompt_cache_ttl or args.no_prompt_cache:
        config = AnthropicLLMConfig(
            api_key=config.api_key,
            model=config.model,
            conflict_model=args.conflict_model or config.conflict_model,
            max_tokens=args.max_tokens or config.max_tokens,
            temperature=config.temperature,
            prompt_cache_enabled=not args.no_prompt_cache,
            prompt_cache_ttl=args.prompt_cache_ttl or config.prompt_cache_ttl,
        )
    client = AnthropicJSONClient(config)

    selected_collections = set(args.collection or ["obligations", "exemption_rules", "tlc_rules"])
    specs = [spec for spec in build_phase5_prompt_specs() if spec.collection in selected_collections]

    report: dict[str, Any] = {
        "runId": run_id,
        "startedAt": datetime.now(UTC).isoformat(),
        "provider": "anthropic",
        "model": config.model,
        "modelRoles": {
            "draftExtraction": config.model,
            "conflictReasoning": config.conflict_model,
            "citationSpanValidation": "deterministic_string_matching_no_ai",
        },
        "maxTokens": config.max_tokens,
        "temperature": config.temperature,
        "promptCache": {
            "enabled": config.prompt_cache_enabled,
            "cacheControl": config.cache_control(),
            "note": "Prompt caching is applied to Anthropic system and user content blocks. Citation span validation remains deterministic and does not use AI.",
        },
        "collections": {},
    }

    for spec in specs:
        relevant_chunks = select_phase5_source_chunks(spec.collection, chunks)
        prompt = render_prompt(spec, relevant_chunks)
        prompt_artifacts = _write_prompt_artifacts(input_dir, spec.collection, spec.system_instructions, prompt, relevant_chunks)
        try:
            llm_response = client.complete_json_array(system=spec.system_instructions, user_prompt=prompt)
        except AnthropicJSONParseError as exc:
            output_artifacts = _write_output_artifacts(
                output_text_dir,
                spec.collection,
                response_text=exc.response_text,
                parsed_json=None,
            )
            raw_path = raw_dir / f"{spec.collection}-raw-response-parse-error.json"
            raw_path.write_text(
                json.dumps(
                    {
                        "runId": run_id,
                        "provider": "anthropic",
                        "model": exc.model,
                        "promptId": spec.prompt_id,
                        "collection": spec.collection,
                        "sourceChunkIds": [chunk["chunk_id"] for chunk in relevant_chunks],
                        "inputArtifacts": prompt_artifacts,
                        "systemInstructions": spec.system_instructions,
                        "userPrompt": prompt,
                        "outputArtifacts": output_artifacts,
                        "responseText": exc.response_text,
                        "parseError": str(exc),
                        "usage": exc.usage,
                        "stopReason": exc.stop_reason,
                        "cacheControl": exc.cache_control,
                        "createdAt": datetime.now(UTC).isoformat(),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            report["collections"][spec.collection] = {
                "promptId": spec.prompt_id,
                "sourceChunkCount": len(relevant_chunks),
                "inputArtifacts": prompt_artifacts,
                "outputArtifacts": output_artifacts,
                "rawResponseFile": str(raw_path),
                "validationFile": None,
                "acceptedRecords": 0,
                "rejectedRecords": 0,
                "conflictRecords": 0,
                "issueCount": 1,
                "parseError": str(exc),
                "usage": exc.usage,
                "stopReason": exc.stop_reason,
                "cacheControl": exc.cache_control,
            }
            continue

        validation_result = validate_ai_records(spec.collection, llm_response.parsed_json, chunk_index)
        output_artifacts = _write_output_artifacts(
            output_text_dir,
            spec.collection,
            response_text=llm_response.response_text,
            parsed_json=llm_response.parsed_json,
        )

        raw_artifact = {
            "runId": run_id,
            "provider": "anthropic",
            "model": llm_response.model,
            "promptId": spec.prompt_id,
            "collection": spec.collection,
            "sourceChunkIds": [chunk["chunk_id"] for chunk in relevant_chunks],
            "inputArtifacts": prompt_artifacts,
            "systemInstructions": spec.system_instructions,
            "userPrompt": prompt,
            "outputArtifacts": output_artifacts,
            "responseText": llm_response.response_text,
            "parsedJson": llm_response.parsed_json,
            "usage": llm_response.usage,
            "stopReason": llm_response.stop_reason,
            "cacheControl": llm_response.cache_control,
            "createdAt": datetime.now(UTC).isoformat(),
        }
        raw_path = raw_dir / f"{spec.collection}-raw-response.json"
        raw_path.write_text(json.dumps(raw_artifact, indent=2), encoding="utf-8")

        validated_path = validated_dir / f"{spec.collection}-validation.json"
        validated_path.write_text(json.dumps(validation_result.model_dump(mode="json"), indent=2), encoding="utf-8")

        report["collections"][spec.collection] = {
            "promptId": spec.prompt_id,
            "sourceChunkCount": len(relevant_chunks),
            "inputArtifacts": prompt_artifacts,
            "outputArtifacts": output_artifacts,
            "rawResponseFile": str(raw_path),
            "validationFile": str(validated_path),
            "acceptedRecords": len(validation_result.accepted_records),
            "rejectedRecords": len(validation_result.rejected_records),
            "conflictRecords": len(validation_result.conflict_records),
            "issueCount": len(validation_result.issues),
            "usage": llm_response.usage,
            "stopReason": llm_response.stop_reason,
            "cacheControl": llm_response.cache_control,
        }

    report["completedAt"] = datetime.now(UTC).isoformat()
    report_path = output_dir / "phase5-anthropic-extraction-report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"runId": run_id, "reportFile": str(report_path), "collections": report["collections"]}, indent=2))


def _write_prompt_artifacts(input_dir: Path, collection: str, system: str, user_prompt: str, chunks: list[dict[str, Any]]) -> dict[str, str]:
    collection_dir = input_dir / collection
    collection_dir.mkdir(parents=True, exist_ok=True)
    system_path = collection_dir / "system-prompt.md"
    user_path = collection_dir / "user-prompt.md"
    chunks_path = collection_dir / "source-chunk-ids.json"
    system_path.write_text(system, encoding="utf-8")
    user_path.write_text(user_prompt, encoding="utf-8")
    chunks_path.write_text(json.dumps([chunk["chunk_id"] for chunk in chunks], indent=2), encoding="utf-8")
    return {
        "systemPromptFile": str(system_path),
        "userPromptFile": str(user_path),
        "sourceChunkIdsFile": str(chunks_path),
    }


def _write_output_artifacts(
    output_dir: Path,
    collection: str,
    *,
    response_text: str,
    parsed_json: list[dict[str, Any]] | None,
) -> dict[str, str | None]:
    collection_dir = output_dir / collection
    collection_dir.mkdir(parents=True, exist_ok=True)
    response_path = collection_dir / "raw-response.txt"
    parsed_path = collection_dir / "parsed-json.json"
    response_path.write_text(response_text, encoding="utf-8")
    if parsed_json is not None:
        parsed_path.write_text(json.dumps(parsed_json, indent=2), encoding="utf-8")
        parsed_path_value: str | None = str(parsed_path)
    else:
        parsed_path_value = None
    return {
        "rawResponseTextFile": str(response_path),
        "parsedJsonFile": parsed_path_value,
    }


if __name__ == "__main__":
    main()
