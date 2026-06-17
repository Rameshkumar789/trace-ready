import os
import unittest

from traceready_ingestion.intelligence.anthropic_client import AnthropicLLMConfig, extract_json_array


class AnthropicClientTest(unittest.TestCase):
    def test_extract_json_array_from_plain_json(self):
        records = extract_json_array('[{"id": "one"}]')

        self.assertEqual(records, [{"id": "one"}])

    def test_extract_json_array_from_fenced_json(self):
        records = extract_json_array('```json\n[{"id": "one"}]\n```')

        self.assertEqual(records, [{"id": "one"}])

    def test_config_reads_model_roles_from_environment(self):
        old_values = {
            key: os.environ.get(key)
            for key in [
                "ANTHROPIC_API_KEY",
                "TRACEREADY_ANTHROPIC_MODEL",
                "TRACEREADY_ANTHROPIC_CONFLICT_MODEL",
                "TRACEREADY_ANTHROPIC_PROMPT_CACHE",
                "TRACEREADY_ANTHROPIC_PROMPT_CACHE_TTL",
            ]
        }
        try:
            os.environ["ANTHROPIC_API_KEY"] = "test-key"
            os.environ["TRACEREADY_ANTHROPIC_MODEL"] = "claude-sonnet-4-6"
            os.environ["TRACEREADY_ANTHROPIC_CONFLICT_MODEL"] = "claude-opus-4-8"
            os.environ["TRACEREADY_ANTHROPIC_PROMPT_CACHE"] = "1"
            os.environ["TRACEREADY_ANTHROPIC_PROMPT_CACHE_TTL"] = "1h"

            config = AnthropicLLMConfig.from_env()

            self.assertEqual(config.model, "claude-sonnet-4-6")
            self.assertEqual(config.conflict_model, "claude-opus-4-8")
            self.assertEqual(config.cache_control(), {"type": "ephemeral", "ttl": "1h"})
        finally:
            for key, value in old_values.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


if __name__ == "__main__":
    unittest.main()
