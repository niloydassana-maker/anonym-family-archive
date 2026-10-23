"""Employer-authored HN threads: Algolia discovery, official API verification.
Sellers' 'Who wants to be hired' threads and applicant replies are excluded.
"""
from datetime import timedelta
import re
from urllib.parse import urlencode

PRIMARY='https://hacker-news.firebaseio.com/v0/item/{}.json'
SEARCH='https://hn.algolia.com/api/v1/'


def harvest_hn(research, process_comment, current_time):
    cutoff=int((current_time()-timedelta(days=research.args.days)).timestamp())
    discovery=SEARCH+'search_by_date?'+urlencode({'tags':'story,author_whoishiring','hitsPerPage':12})
    try: stories=research.get(discovery,api=True).get('hits',[])
    except Exception as e:
        research.error('hn_thread_discovery',discovery,e); return
    threads=[]
    for hit in stories:
        title=hit.get('title') or ''
        if not (re.match(r'^Ask HN: Who is hiring\?',title,re.I) or re.match(r'^Ask HN: Freelancer\?',title,re.I)): continue
        identifier=hit.get('objectID','')
        if not str(identifier).isdigit(): continue
        if current_time().timestamp()-hit.get('created_at_i',0)>45*86400: continue
        try:
            thread=research.get(PRIMARY.format(identifier),api=True)
            if thread.get('by')!='whoishiring' or thread.get('type')!='story' or thread.get('title')!=title or thread.get('dead') or thread.get('deleted'): continue
            if current_time().timestamp()-thread.get('time',0)>45*86400: continue
            threads.append(thread)
        except Exception as e: research.error('hn_primary_thread',PRIMARY.format(identifier),e)
    seen=set()
    for thread in threads[:3]:
        for page in range(getattr(research.args,'max_feed_pages',10)):
            endpoint=SEARCH+'search_by_date?'+urlencode({'tags':f"comment,story_{thread['id']}",'numericFilters':f'created_at_i>{cutoff}','hitsPerPage':100,'page':page})
            try: data=research.get(endpoint,api=True)
            except Exception as e:
                research.error('hn_comment_discovery',endpoint,e); break
            for hit in data.get('hits',[]):
                identifier=hit.get('objectID','')
                if not str(identifier).isdigit() or identifier in seen: continue
                seen.add(identifier)
                if hit.get('parent_id') and str(hit['parent_id'])!=str(thread['id']): continue
                primary=PRIMARY.format(identifier)
                try:
                    item=research.get(primary,api=True)
                    if item.get('type')!='comment' or item.get('parent')!=thread['id'] or item.get('dead') or item.get('deleted'): continue
                    lead=process_comment(item,thread,research)
                    if lead: research.leads.append(lead)
                    if len(research.leads)>=research.args.limit: return
                except Exception as e: research.error('hn_primary_comment',primary,e)
            if page+1>=data.get('nbPages',1): break
