"""Negative regressions from actual saved Jobicy and WordPress API responses.
No generated leads, test payloads, network mocks, or modifications to old tests.
"""
import json
from pathlib import Path
import unittest
import hunt_100_leads_master as master
from lead_quality import validated_contacts, task_fit

RUN = Path(__file__).parent/'output/master_20261023T113628619235Z'


class ActualFalsePositiveRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.jobs={}; cls.wordpress=[]
        audit=json.loads((RUN/'audit.json').read_text('utf-8'))
        for receipt in audit['receipts']:
            if 'jobicy.com/api/' not in receipt['url'] and 'jobspresso.co/wp-json/' not in receipt['url']: continue
            data=json.loads(Path(receipt['file']).read_bytes())
            if isinstance(data,dict):
                cls.jobs.update({j['id']:j for j in data.get('jobs',[])})
            elif isinstance(data,list): cls.wordpress.extend(data)

    def test_gartner_accessibility_email_and_phone_rejected(self):
        job=self.jobs[143967]
        accepted,rejected=validated_contacts(job['jobDescription'],job['url'])
        self.assertNotIn('applicantaccommodations@gartner.com',{c['value'] for c in accepted})
        self.assertNotIn('+12039640096',{c['value'] for c in accepted})
        self.assertTrue(any(c['value']=='applicantaccommodations@gartner.com' for c in rejected))
        self.assertTrue(any(c['value']=='+12039640096' for c in rejected))

    def test_unrelated_roles_not_qualified_from_boilerplate(self):
        for identifier in (143967,156516,156488,156486,156485):
            job=self.jobs[identifier]
            with self.subTest(title=job['jobTitle']):
                self.assertFalse(task_fit(job['jobTitle'],job['jobDescription']))

    def test_accommodation_mailboxes_not_promoted_to_hiring_contacts(self):
        for identifier in (153899,153871):
            job=self.jobs[identifier]
            accepted,_=validated_contacts(job['jobDescription'],job['url'])
            self.assertFalse(any('accommodat' in c['value'].lower() for c in accepted))

    def test_php_role_is_not_a_n8n_automation_match(self):
        job=self.jobs[156456]
        self.assertFalse(task_fit(job['jobTitle'],job['jobDescription']))

    def test_wordpress_local_date_is_not_assumed_utc(self):
        job=next(j for j in self.wordpress if j.get('date_gmt'))
        self.assertIsNone(master.date(job['date']))
        self.assertIsNotNone(master.date(job['date_gmt']+'+00:00'))


if __name__=='__main__': unittest.main()
