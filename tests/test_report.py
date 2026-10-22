import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from leadevidencekit import render_markdown, validate_report
from leadevidencekit.report import safe_url

ROOT = Path(__file__).resolve().parents[1]


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.packet = json.loads((ROOT / 'examples/synthetic.json').read_text())

    def test_synthetic_example_and_coverage(self):
        self.assertEqual(validate_report(self.packet), [])
        output = render_markdown(self.packet)
        self.assertIn('## Attributed findings', output)
        self.assertIn('trade: blocked; attributed: false', output)
        self.assertIn('purchasing scale remains unknown', output)

    def test_source_failure_cannot_support_fact(self):
        for status in ['candidate', 'blocked', 'not_found', 'not_run']:
            with self.subTest(status=status):
                self.packet['sources'][0]['status'] = status
                self.assertTrue(validate_report(self.packet))

    def test_unattributed_source_cannot_support_fact(self):
        self.packet['sources'][0]['attributed'] = False
        self.assertTrue(validate_report(self.packet))

    def test_unconfirmed_identity_still_allows_candidates(self):
        self.packet['identity'] = 'unconfirmed'
        self.assertTrue(validate_report(self.packet))
        self.packet['claims'][0]['kind'] = 'candidate'
        self.assertEqual(validate_report(self.packet), [])

    def test_read_requires_excerpt(self):
        self.packet['sources'][0]['quote'] = '  '
        self.assertTrue(validate_report(self.packet))

    def test_refs_must_exist_and_facts_need_refs(self):
        for refs in [[], ['missing'], [42], 'site']:
            with self.subTest(refs=refs):
                self.packet['claims'][0]['source_ids'] = refs
                self.assertTrue(validate_report(self.packet))

    def test_duplicate_source_ids(self):
        self.packet['sources'].append(copy.deepcopy(self.packet['sources'][0]))
        self.assertTrue(validate_report(self.packet))

    def test_malformed_data_returns_errors(self):
        for packet in [None, [], {}, {'subject': 42}, {'subject': 'X', 'identity': []}]:
            with self.subTest(packet=packet):
                self.assertTrue(validate_report(packet))
        for field in ['sources', 'claims']:
            for bad in [None, 42, [None], [[]]]:
                packet = copy.deepcopy(self.packet)
                packet[field] = bad
                self.assertTrue(validate_report(packet))
        for field in ['status', 'id', 'attributed', 'url', 'quote']:
            packet = copy.deepcopy(self.packet)
            packet['sources'][0][field] = []
            self.assertTrue(validate_report(packet))

    def test_invalid_claim_kinds_and_identity(self):
        for field, bad in [('identity', {}), ('identity', 'guessed')]:
            packet = copy.deepcopy(self.packet)
            packet[field] = bad
            self.assertTrue(validate_report(packet))
        self.packet['claims'][0]['kind'] = []
        self.assertTrue(validate_report(self.packet))

    def test_urls_reject_active_content_and_credentials(self):
        for value in ['javascript:alert(1)', 'file:///etc/passwd',
                      'https://user:pass@example.test', 'https://example.test/x>bad',
                      'https://example.test/\n#injected', 'https://example.test:bad',
                      'https://example.test/[x]', 'https://[broken', None]:
            with self.subTest(value=value):
                self.assertFalse(safe_url(value))
        self.assertTrue(safe_url('https://example.test/about?a=1&b=2'))

    def test_untrusted_prose_is_inert_and_not_mutated(self):
        self.packet['subject'] = '<script>alert(1)</script>\n# heading'
        self.packet['claims'][0]['text'] = '![x](https://example.test) <img src=x>'
        original = copy.deepcopy(self.packet)
        output = render_markdown(self.packet)
        self.assertNotIn('<script>', output)
        self.assertNotIn('<img', output)
        self.assertNotIn('![x](', output)
        self.assertEqual(self.packet, original)

    def test_render_rejects_invalid_packet(self):
        with self.assertRaises(ValueError):
            render_markdown({})

    def test_empty_report_has_no_invented_findings(self):
        output = render_markdown({'subject': 'Unknown', 'identity': 'unconfirmed',
                                  'sources': [], 'claims': []})
        self.assertIn('None recorded.', output)
        self.assertNotIn('★★★★★', output)

    def test_cli_valid_and_invalid_inputs(self):
        env = dict(os.environ, PYTHONPATH=str(ROOT / 'src'), PYTHONDONTWRITEBYTECODE='1')
        valid = subprocess.run([sys.executable, '-m', 'leadevidencekit',
                                str(ROOT / 'examples/synthetic.json'), '--check'],
                               capture_output=True, text=True, env=env)
        self.assertEqual(valid.returncode, 0, valid.stderr)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'invalid.json'
            for content in ['{', '{}', 'null']:
                path.write_text(content)
                result = subprocess.run([sys.executable, '-m', 'leadevidencekit', str(path)],
                                        capture_output=True, text=True, env=env)
                self.assertEqual(result.returncode, 1)
                self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()
