"""Job Hunter V10. Standard library only. No AI or user secrets."""
import concurrent.futures as cf
import datetime as dt
import html,json,os,re,sys,time,unittest,urllib.request
from pathlib import Path
from xml.etree import ElementTree as ET

SOURCES={
 'UNOPS':'https://rss.careers.unops.org/',
 'UN Careers':'https://careers.un.org/jobfeed?isPage=true',
 'UNDP Europe':'https://jobs.undp.org/rss_feeds/RER.xml',
 'UNDP Contracts':'https://jobs.undp.org/rss_feeds/ICE.xml'}
TRACKS={
 'Construction': ['construction engineer','construction manager','construction specialist','site engineer','resident engineer','engineering officer','clerk of works','construction supervision','civil works','rehabilitation'],
 'Infrastructure':['civil engineer','structural engineer','road engineer','bridge engineer','infrastructure engineer','infrastructure specialist','building services engineer','geotechnical engineer','energy efficiency engineer','reinforced concrete','pavement'],
 'WASH':['wash engineer','water engineer','sanitation engineer','water supply','water treatment','sewerage','wastewater','boreholes'],
 'Contracts':['quantity surveyor','fidic','contract manager','contracts manager','cost engineer','works contracts','bill of quantities','bills of quantities','boq'],
 'Facilities':['facilities manager','facility manager','common premises','building maintenance','refurbishment','property management'],
 'Architecture':['architect','heritage conservation','restoration','urban planner','housing reconstruction','architectural design']}
PHYSICAL=['construction','civil works','building','buildings','concrete','water supply','sewerage','wastewater','boq','fidic','pavement','roads','bridges']
DIGITAL=['software','cloud','digital infrastructure','digital public infrastructure','data engineer','solutions architect','enterprise architect','data architect','it infrastructure','cybersecurity']

def norm(s): return re.sub(r'[^a-z0-9]+',' ',html.unescape(re.sub(r'<[^>]*>',' ',s or '')).lower()).strip()
def has(s,p): return (' '+norm(p)+' ') in (' '+norm(s)+' ')
def rank(title,description,source):
 t,d=norm(title),norm(description)
 if any(has(t,x) for x in ['intern','internship','driver','finance officer','communications officer','human resources']): return 0,''
 if any(has(t+' '+d,x) for x in ['internal candidates only','internal applicants only']): return 0,''
 if any(has(t,x) for x in DIGITAL): return 0,''
 if any(has(t+' '+d,x) for x in DIGITAL) and not any(has(t+' '+d,x) for x in PHYSICAL): return 0,''
 scores={k:sum(24 if has(t,p) else 8 if has(d,p) else 0 for p in terms) for k,terms in TRACKS.items()}
 track=max(scores,key=scores.get); technical=scores[track]
 if technical<16:return 0,''
 bonus=8 if source=='UNOPS' else 4
 if any(has(t+' '+d,x) for x in ['sarajevo','bosnia','western balkans']):bonus+=10
 return technical+bonus,track

def parse(raw,source):
 root=ET.fromstring(raw); out=[]
 for item in root.iter():
  if item.tag.split('}')[-1] not in ('item','entry'):continue
  fields={c.tag.split('}')[-1]:c for c in item}
  def val(k):
   e=fields.get(k);return ''.join(e.itertext()).strip() if e is not None else ''
  link=val('link'); le=fields.get('link')
  if not link and le is not None:link=le.get('href','')
  if not link.startswith(('https://','http://')):continue
  title=html.unescape(val('title')); desc=val('description') or val('summary') or val('content')
  score,track=rank(title,desc,source)
  if score:out.append(dict(title=title,url=link,source=source,score=score,track=track,posted=val('pubDate') or val('updated'),deadline='Not verified'))
 return out

def load_source(name,url):
 start=time.perf_counter()
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'DamirJobHunter/10 public RSS reader'})
  with urllib.request.urlopen(req,timeout=18) as r:raw=r.read(4_000_001)
  if len(raw)>4_000_000:raise ValueError('Response exceeds size limit')
  root=ET.fromstring(raw)
  if root.tag.split('}')[-1] not in ('rss','feed','RDF'):raise ValueError('Not an RSS/Atom feed')
  jobs=parse(raw,name)
  return name,jobs,dict(ok=True,message=f'{len(jobs)} matching entries',seconds=round(time.perf_counter()-start,2))
 except Exception as e:return name,[],dict(ok=False,message=f'{type(e).__name__}: {str(e)[:180]}',seconds=round(time.perf_counter()-start,2))

def collect(previous,results):
 old={j['url']:j for j in previous.get('jobs',[])}; merged={}; health={}; retained=0
 for name,jobs,status in results:
  health[name]=status
  if not status['ok']:
   jobs=[dict(j,retained=True) for j in old.values() if j['source']==name];retained+=len(jobs)
  for j in jobs:
   j=dict(j);j['new']=j['url'] not in old
   merged.setdefault(j['url'],j)
 return dict(updated=dt.datetime.now(dt.timezone.utc).isoformat(),jobs=sorted(merged.values(),key=lambda j:(-j['score'],j['title'])),sources=health,retained=retained)

def run():
 site=Path('site');site.mkdir(exist_ok=True)
 old={}
 try:
  req=urllib.request.Request(os.environ.get('PREVIOUS_DATA_URL',''),headers={'User-Agent':'DamirJobHunter/10'})
  with urllib.request.urlopen(req,timeout=10) as r:old=json.load(r)
 except Exception:pass
 with cf.ThreadPoolExecutor(max_workers=4) as pool:
  results=list(pool.map(lambda x:load_source(*x),SOURCES.items()))
 data=collect(old,results)
 (site/'jobs.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
 summary=f"# Job Hunter V10\n\n{len(data['jobs'])} matching jobs. {sum(s['ok'] for s in data['sources'].values())}/{len(SOURCES)} feeds responded.\n\n"
 summary+='\n'.join(f"- {n}: {s['message']}" for n,s in data['sources'].items())
 summary+='\n\nResults are discovery leads, not verified eligibility or open-deadline decisions.'
 if os.environ.get('GITHUB_STEP_SUMMARY'):Path(os.environ['GITHUB_STEP_SUMMARY']).write_text(summary,encoding='utf-8')
 print(summary)

class Tests(unittest.TestCase):
 def test_positive_tracks(self):
  for track,terms in TRACKS.items():
   for title in terms:
    s,tr=rank(title,'','UNOPS');self.assertGreater(s,0,title)
 def test_negative(self):
  for title in ['Driver','Construction Intern','Cloud Infrastructure Engineer','Solutions Architect','Finance Officer','Digital Public Infrastructure Specialist']:
   self.assertEqual(rank(title,'construction project Sarajevo','UNOPS')[0],0,title)
 def test_internal(self):self.assertEqual(rank('Construction Engineer','Internal candidates only','UNOPS')[0],0)
 def test_boundaries(self):self.assertFalse(has('international','intern'))
 def test_rss(self):
  raw=b'<rss><channel><item><title>Construction Engineer</title><link>https://example.org/1</link></item></channel></rss>'
  self.assertEqual(len(parse(raw,'UNOPS')),1)
 def test_atom(self):
  raw=b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Site Engineer</title><link href="https://example.org/2"/></entry></feed>'
  self.assertEqual(len(parse(raw,'UNOPS')),1)
 def test_bad_link(self):
  self.assertEqual(parse(b'<rss><item><title>Construction Engineer</title><link>javascript:alert(1)</link></item></rss>','UNOPS'),[])
 def test_retention(self):
  old={'jobs':[dict(url='https://x',source='UNOPS',title='Site Engineer',score=24)]}
  d=collect(old,[('UNOPS',[],dict(ok=False,message='403'))]);self.assertEqual(d['retained'],1)
 def test_empty_success(self):self.assertEqual(collect({},[('UNOPS',[],dict(ok=True))])['jobs'],[])
 def test_dedupe(self):
  j=dict(url='https://x',source='UNOPS',title='Site Engineer',score=24)
  self.assertEqual(len(collect({},[('UNOPS',[j,j],dict(ok=True))])['jobs']),1)

if __name__=='__main__':
 if sys.argv[1:]==['test']:unittest.main(argv=[sys.argv[0]])
 else:run()
