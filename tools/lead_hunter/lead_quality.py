"""Conservative purpose/attribution gates; extraction never certifies ownership."""
import html
from html.parser import HTMLParser
import re
from urllib.parse import urlparse
from hunt_leads import contacts

BAD_PURPOSE = re.compile(r'accommodat|disabilit|accessibility|privacy|data protection|legal notice|copyright|report.{0,30}(?:fraud|scam)|(?:fraud|scam).{0,30}report|technical (?:issues|support)|customer support|unsubscribe|example (?:email|number|contact)|sample (?:email|number)|e\.g\.|for example|do not (?:email|contact)|not (?:accept|process).{0,25}(?:application|resume)', re.I)
BAD_PURPOSE = re.compile(BAD_PURPOSE.pattern + r'|alternative selection process|fraudulent representation|report (?:them|such|any suspicious)|outside these channels|never request fees|(?:sample|dummy|placeholder) (?:data|address|record)|customer(?:\x27s)? (?:email|phone)|client(?:\x27s)? (?:email|number)', re.I)
GOOD_PURPOSE = re.compile(r'\b(?:apply|application|recruit(?:ment|er|ing)?|hiring|email|e-mail|contact|reach|whats\s*app|phone|telephone|mobile|linkedin|questions|submit|send (?:your|a|an|me|us|to)|(?:please|pls|kindly) (?:send|share)|share your details|DM me|message me)\b', re.I)
ROLE_NO = re.compile(r'\b(?:customer success|people operations|account executive|recruiter|sales representative|account manager|content strategist|content writer|copywriter|product designer|analyst relations|threat detection analyst|tutor|unpaid|commission.only)\b', re.I)
STRONG_TITLE = re.compile(r'\bn8n\b|\bmake\.com\b|\bZapier\b|\bLangGraph\b|\bFastAPI\b|\bRAG\b|\bSupabase\b|\bUiPath\b|'
                          r'(?:AI|LLM|GenAI|agent|copilot|chatbot|bot|workflow|CRM|process|task)\s+(?:\w+\s+)?(?:automation|engineer|developer|architect|integration|setup|build|development)|'
                          r'(?:API|backend|data pipeline|integration|automation|scraping|crawler)\s+(?:\w+\s+)?(?:engineer|developer|architect|specialist|script|support|build)|'
                          r'Python\s+(?:\w+\s+)?(?:engineer|developer|architect|backend|script|dashboard|platform|automation)|'
                          r'\b(?:chatbot|bot|crawler|scraper)\b', re.I)
NICHE = [re.compile(x,re.I) for x in (r'\bn8n\b',r'\bmake\.com\b',r'\blanggraph\b',r'\bfastapi\b',r'\bRAG\b',r'\bwebhooks?\b',r'workflow automation',r'CRM (?:integration|automation)',r'API integration',r'AI agents?',r'automation script',r'bot development')]
HELP_TITLE = re.compile(r'^(?:how (?:do|can|to)|help(?:!|\s+with)|question|tutorial|guide|showcase)\b',re.I)
SELLER_INTRO = re.compile(r'\b(?:I (?:offer|provide|am available)|we (?:offer|provide)|looking for (?:work|clients)|seeking (?:work|clients)|for hire)\b',re.I)


class Blocks(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.blocks=[]; self.parts=[]; self.skip=[]; self.heading=False; self.section=''
        self.feed(source); self.flush()
    def flush(self):
        value=''.join(self.parts).strip(); self.parts=[]
        if value:
            self.blocks.append((value,self.section))
    def handle_starttag(self,tag,attrs):
        if tag in ('aside','blockquote','script','style','noscript','footer','header','nav'):
            self.skip.append(tag); return
        if self.skip: return
        if tag in ('p','li','div','br','hr') or re.fullmatch('h[1-6]',tag): self.flush()
        if re.fullmatch('h[1-6]',tag): self.heading=True
        if tag=='a':
            href=dict(attrs).get('href','')
            self.parts.append('<a href="'+html.escape(href,quote=True)+'">')
    def handle_startendtag(self,tag,attrs):
        if not self.skip and tag in ('br','hr'): self.flush()
    def handle_endtag(self,tag):
        if self.skip:
            if self.skip[-1]==tag: self.skip.pop()
            return
        if tag=='a': self.parts.append('</a>')
        if re.fullmatch('h[1-6]',tag):
            self.section=re.sub('<[^>]+>',' ',''.join(self.parts)); self.heading=False
        if tag in ('p','li','div') or re.fullmatch('h[1-6]',tag): self.flush()
    def handle_data(self,data):
        if not self.skip: self.parts.append(html.escape(data))


def task_fit(title,body):
    """Avoid role false positives from generic 'engineer' or company boilerplate."""
    if re.search(r'\b(?:corporate trainer|AI trainer|workshop facilitator|PHP)\b', title, re.I): return False
    if ROLE_NO.search(title): return False
    if STRONG_TITLE.search(title): return True
    if re.search(r'\b(?:FastAPI|LangGraph|AI orchestration|n8n|make\.com|automation|bot|chatbot|copilot)\b', title, re.I) and re.search(r'\b(?:build|complete|fix|setup|integrat\w*|MVP|develop\w*|automate|dashboard)\b', title, re.I): return True
    if re.search(r'\b(?:agent|database|backend|pipeline|API)\b', title, re.I) and re.search(r'\b(?:setup|build|develop\w*|architect)\b', title, re.I):
        if STRONG_TITLE.search(body[:400]) or sum(bool(p.search(body)) for p in NICHE)>=1: return True
    engineering = re.search(r'\b(?:software|backend|python|data|AI|automation|integration|developer|engineer|architect)\b',title,re.I)
    return bool(engineering and (sum(bool(p.search(body)) for p in NICHE)>=1 or re.search(r'\b(?:workflow automation|API integration|AI agent|LLM|FastAPI|LangGraph|RAG|n8n|make\.com|bot)\b', body, re.I)))


def validated_contacts(source, source_url):
    accepted=[]; rejected=[]; seen=set()
    for block,section in Blocks(source or '').blocks:
        _,items=contacts(block)
        text=html.unescape(re.sub('<[^>]+>',' ',block))
        context=section+' '+text
        for item in items:
            key=item['kind'],item['value']
            value=item['value']; reason=''
            if BAD_PURPOSE.search(context): reason='non_application_or_example_contact_context'
            elif not GOOD_PURPOSE.search(context): reason='contact_purpose_or_owner_unconfirmed'
            elif item['kind']=='email':
                local,domain=value.lower().rsplit('@',1)
                if (domain in ('example.com','example.org','example.net','test.com','domain.com') or domain.endswith(('.invalid','.example','.test','.localhost','.png','.jpg','.webp','.svg'))
                    or re.search(r'accommodat|privacy|noreply|no-reply|donotreply|fraud|abuse',local)
                    or local in ('yourname','your.email','name','username','someone','support','helpdesk')):
                    reason='placeholder_or_non_hiring_mailbox'
            elif item['kind'] in ('phone','whatsapp_number'):
                digits=re.sub(r'\D','',value)
                if not value.startswith('+') or value.startswith('+0'): reason='country_code_not_established'
                elif len(set(digits))<=2 or digits in ('1234567890','0123456789'): reason='placeholder_phone_pattern'
                elif not re.search(r'phone|tel:|telephone|mobile|whats\s*app|wa\.me|whatsapp\.com|call|contact.{0,10}(?:no|number)',block,re.I): reason='phone_purpose_unconfirmed'
            elif item['kind']=='linkedin':
                slug=urlparse(value).path.split('/in/',1)[-1].lower()
                if slug in ('example','username','yourname','your-profile','profile'): reason='placeholder_profile'
            if reason:
                rejected.append({**item,'source_url':source_url,'reason':reason,'context':context[:700]})
                continue
            if key not in seen:
                accepted.append({**item,'contact_context':context[:700], 'purpose':'explicit_contact_context_not_ownership_verification'})
                seen.add(key)
    # Shared extractor also identifies contacts in ignored blocks or ambiguous raw text.
    _,all_items=contacts(source or '')
    for item in all_items:
        if (item['kind'],item['value']) not in seen and not any(r['kind']==item['kind'] and r['value']==item['value'] for r in rejected):
            rejected.append({**item,'source_url':source_url,'reason':'outside_attributable_contact_block'})
    return accepted,rejected
