"""Positive regression: a genuine primary buyer project need not publish email.
Uses unchanged archived Freelancer API response bytes, never invented fixtures.
"""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import hunt_100_leads_master as master
from test_master_real_sources import config

RUN=Path(__file__).parent/'output/master_20261023T115232769524Z'


class RealApplicationRoutes(unittest.TestCase):
    def real_project(self, identifier):
        for archive in (RUN,RUN.parent/'master_20261023T120109773081Z',RUN.parent/'master_20261023T120811711519Z'):
            audit=json.loads((archive/'audit.json').read_text('utf-8'))
            for receipt in audit['receipts']:
                if '/projects/0.1/projects/active/' not in receipt['url']: continue
                data=json.loads(Path(receipt['file']).read_bytes())
                for project in data.get('result',{}).get('projects',[]):
                    if project['id']==identifier: return project
        self.fail(f'Actual archived buyer project missing: {identifier}')

    def test_us_client_location_is_not_an_applicant_restriction(self):
        project=self.real_project(40776255)
        self.assertIn('US-based client',project['description'])
        with TemporaryDirectory() as tmp:
            args=config(); args.contact_policy='any-route'
            lead=master.process_project(project,master.Research(args,Path(tmp)))
            self.assertIsNotNone(lead)

    def test_real_fastapi_mvp_and_agent_setup_are_not_discarded(self):
        with TemporaryDirectory() as tmp:
            args=config(); args.contact_policy='any-route'
            research=master.Research(args,Path(tmp))
            for identifier in (40782067,40780416,40778969):
                self.assertIsNotNone(master.process_project(self.real_project(identifier),research),identifier)

    def test_trainer_only_role_is_outside_implementation_work(self):
        with TemporaryDirectory() as tmp:
            args=config(); args.contact_policy='any-route'
            research=master.Research(args,Path(tmp))
            self.assertIsNone(master.process_project(self.real_project(40775872),research))

    def test_active_marketplace_showcases_are_not_buyer_requests(self):
        with TemporaryDirectory() as tmp:
            args=config(); args.contact_policy='any-route'
            research=master.Research(args,Path(tmp))
            for identifier in (40782970,40778097):
                self.assertIsNone(master.process_project(self.real_project(identifier),research),identifier)
            self.assertTrue(all('portfolio_showcase_or_seller_not_buyer_need' in x['reasons'] for x in research.excluded))

    def test_actual_conflicting_budget_is_not_silently_presented_as_agreed(self):
        with TemporaryDirectory() as tmp:
            args=config(); args.contact_policy='any-route'
            lead=master.process_project(self.real_project(40775210),master.Research(args,Path(tmp)))
            self.assertIsNotNone(lead)
            self.assertIn('$1,500',lead['budget_mentions'])
            self.assertIn('brief_budget_conflicts_with_structured_listing_confirm_before_quoting',lead['review_flags'])

    def test_identical_live_repost_is_not_counted_as_two_buyers(self):
        with TemporaryDirectory() as tmp:
            args=config(); args.contact_policy='any-route'
            research=master.Research(args,Path(tmp))
            research.leads=[master.process_project(self.real_project(i),research) for i in (40780884,40780885)]
            retained,duplicates=master.finalize_candidates(research)
            self.assertEqual(len(retained),1)
            self.assertEqual(retained[0]['lead_id'],'FL-40780885')
            self.assertEqual(len(duplicates),1)
            self.assertIn('identical_full_brief',duplicates[0]['reason'])

    def test_keep_real_active_project_with_native_application_route(self):
        audit=json.loads((RUN/'audit.json').read_text('utf-8'))
        project=None
        for receipt in audit['receipts']:
            if '/projects/0.1/projects/active/' not in receipt['url']: continue
            data=json.loads(Path(receipt['file']).read_bytes())
            project=next((p for p in data.get('result',{}).get('projects',[]) if p['id']==40782504),project)
        self.assertIsNotNone(project,'Actual archived buyer project missing')
        self.assertEqual(project['status'],'active')
        with TemporaryDirectory() as tmp:
            args=config(); args.contact_policy='any-route'
            research=master.Research(args,Path(tmp))
            lead=master.process_project(project,research)
            self.assertIsNotNone(lead)
            self.assertEqual(lead['lead_id'],'FL-40782504')
            self.assertEqual(lead['contact_kind'],'platform_application')
            self.assertEqual(lead['coordinate_count'],0)
            self.assertEqual(lead['email'],[])
            self.assertIn('250.0 - 750.0',lead['budget'])
            self.assertIn('Freelancer proposal route',lead['contact_route'])
            args.contact_policy='direct-only'
            self.assertIsNone(master.process_project(project,research))


if __name__=='__main__': unittest.main()
