"""Checks the additional false contacts observed in the actual five-day live run."""
import json
from pathlib import Path
import unittest
from lead_quality import validated_contacts

RUN=Path(__file__).parent/'output/master_20261023T114906529492Z'


class FurtherRealContactRegressions(unittest.TestCase):
    def test_fraud_support_and_alternative_assessment_routes_are_not_outreach_contacts(self):
        audit=json.loads((RUN/'audit.json').read_text('utf-8'))
        checked=set()
        for receipt in audit['receipts']:
            if 'jobicy.com/api/jobs?' in receipt['url']:
                jobs=json.loads(Path(receipt['file']).read_bytes()).get('jobs',[])
                for job in jobs:
                    if job.get('id') not in (156284,156280,156289,151239,151253): continue
                    accepted,rejected=validated_contacts(job['jobDescription'],job['url'])
                    old='support@clickup.com' if 'ClickUp' in job['companyName'] else 'careers@launchdarkly.com'
                    self.assertNotIn(old,{c['value'] for c in accepted})
                    self.assertIn(old,{c['value'] for c in rejected})
                    checked.add(job['id'])
            if 'remoteok.com/api' in receipt['url']:
                jobs=json.loads(Path(receipt['file']).read_bytes())
                for job in jobs:
                    if str(job.get('id'))!='1137551': continue
                    accepted,rejected=validated_contacts(job['description'],job['url'])
                    self.assertNotIn('careers@duckduckgo.com',{c['value'] for c in accepted})
                    self.assertIn('careers@duckduckgo.com',{c['value'] for c in rejected})
                    checked.add(1137551)
        self.assertEqual(checked,{156284,156280,156289,151239,151253,1137551})


if __name__=='__main__': unittest.main()
