"""Regression checks on genuine saved source responses; no mocked APIs or invented leads.
Run from this directory with: python -m unittest test_master_real_sources -v
"""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
import hunt_100_leads_master as master
from verify_real_sources import cooked_posts

ARCHIVE = Path(__file__).resolve().parents[2] / 'war-log/audits/cash-deadline-20261023'


def config():
    return SimpleNamespace(delay=0, max_requests=1, max_batches=0, days=3650,
                           no_profiles=True, suppressed=set(), limit=100, deliverables_dir=None)


class RealSourceRegressions(unittest.TestCase):
    def test_all_four_coordinates_with_statuses(self):
        kinds = set()
        for path in ARCHIVE.glob('lead-*.json'):
            for body in cooked_posts(json.loads(path.read_text('utf-8-sig'))):
                extracted = master.clean_contacts(body)
                for field in master.FIELDS:
                    values = extracted['emails' if field == 'email' else field]
                    self.assertEqual(extracted[field+'_status'], 'published_candidate' if values else 'not_found_in_scanned_content')
                    if values: kinds.add(field)
        self.assertEqual(kinds, set(master.FIELDS))

    def test_closed_buyer_is_rejected_from_real_topic(self):
        topic = json.loads((ARCHIVE/'lead-n8n-317595.json').read_text('utf-8-sig'))
        with TemporaryDirectory() as tmp:
            run = master.Research(config(), Path(tmp))
            lead = master.process_topic(topic, 'https://community.n8n.io', run)
            self.assertIsNone(lead)
            self.assertTrue(any('closed' in reason for x in run.excluded for reason in x['reasons']), run.excluded)

    def test_real_topic_suppression_and_evidence(self):
        topic = json.loads((ARCHIVE/'lead-n8n-323364.json').read_text('utf-8-sig'))
        # Append only authentic fetched reply batches from the same topic.
        for p in ARCHIVE.glob('lead-n8n-323364-posts-*.json'):
            data = json.loads(p.read_text('utf-8-sig'))
            topic['post_stream']['posts'].extend(data.get('post_stream', {}).get('posts', []))
        with TemporaryDirectory() as tmp:
            run = master.Research(config(), Path(tmp))
            lead = master.process_topic(topic, 'https://community.n8n.io', run)
            self.assertIsNotNone(lead)
            self.assertIn('alvaro@wellbayt.com', lead['email'])
            self.assertEqual(lead['buyer_username'], 'Alvaro_Zapata')
            self.assertEqual(lead['coordinate_count'], sum(bool(lead[x]) for x in master.FIELDS))
            self.assertLessEqual(lead['coordinate_count'], 4)
            self.assertTrue(all(e['source_url'].startswith('https://community.n8n.io/t/323364/') for e in lead['contact_evidence']))
            self.assertIsNone(lead['can_direct_message'])
            run.args.suppressed = {'alvaro@wellbayt.com'}
            self.assertIsNone(master.process_topic(topic, 'https://community.n8n.io', run))

    def test_output_with_empty_results_is_valid(self):
        with TemporaryDirectory() as tmp:
            run = master.Research(config(), Path(tmp))
            master.write_results(run)
            self.assertEqual(json.loads((Path(tmp)/'MASTER_100_LEADS.json').read_text('utf-8')), [])
            self.assertIn('whatsapp_number', (Path(tmp)/'MASTER_100_LEADS.csv').read_text('utf-8-sig'))
            self.assertNotIn('Verified Active', (Path(tmp)/'MASTER_100_LEADS_REPORT.md').read_text('utf-8'))


if __name__ == '__main__':
    unittest.main()
