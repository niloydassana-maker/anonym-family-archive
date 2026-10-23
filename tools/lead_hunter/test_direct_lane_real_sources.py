"""Direct-lane checks using a saved, genuine primary topic response."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import hunt_100_leads_master as master
from test_master_real_sources import config


RUN = Path(__file__).parent / 'output' / 'master_20261023T122755030037Z'


def closed_vendor_topic():
    audit = json.loads((RUN / 'audit.json').read_text('utf-8'))
    for receipt in audit['receipts']:
        raw = Path(receipt['file']).read_bytes()
        try:
            topic = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if topic.get('id') == 321244:
            return topic
    raise AssertionError('Actual saved n8n topic response missing')


class DirectLaneRealSources(unittest.TestCase):
    def test_closed_creator_marketplace_is_not_a_direct_client_lead(self):
        topic = closed_vendor_topic()
        self.assertTrue(topic['closed'])
        with TemporaryDirectory() as tmp:
            args = config(); args.contact_policy = 'direct-only'; args.direct_first = True
            research = master.Research(args, Path(tmp))
            self.assertIsNone(master.process_topic(topic, 'https://community.n8n.io', research))
            reasons = {r for row in research.excluded for r in row['reasons']}
            self.assertIn('topic_marked_closed', reasons)
            self.assertIn('vendor_marketplace_or_creator_program_not_client_demand', reasons)


if __name__ == '__main__':
    unittest.main()
