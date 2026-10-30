#!/usr/bin/env python3
"""Build a lossless, local-only normalized view of saved BBPlus records."""
import csv, hashlib, html, json, re, shutil
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit
from datetime import datetime, timezone
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'
SRC=ROOT/'bbplus_all'/'questions.jsonl'
def dump(name,obj):
 (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def build():
 OUT.mkdir(exist_ok=True); (OUT/'assets').mkdir(exist_ok=True)
 rows=[json.loads(x) for x in SRC.read_text(encoding='utf-8').splitlines() if x.strip()]
 assets=json.loads((ROOT/'bbplus_dec2025'/'downloaded_assets.json').read_text())
 for rel in set(assets.values()):
  src=ROOT/'bbplus_dec2025'/rel
  if src.exists(): shutil.copy2(src,OUT/'assets'/src.name)
 records=[]; groups=defaultdict(list); tests=defaultdict(list)
 for r in rows:
  u=r['source_url']; path=urlsplit(u).path; m=re.search(r'/courses/(20\d{2})-([^/]+)/lessons/([^/]+)/quizzes/([^/]+)',path)
  year=int(m[1]) if m else None; month=m[2] if m else None; form=re.search(r'form-([a-z])',path); mod=re.search(r'-(?:english|math)-m(\d+)',path)
  subject='Math' if '-math-' in path else 'Reading and Writing' if '-english-' in path else None
  soup=BeautifulSoup(r.get('question_html') or '', 'html.parser'); passage=soup.select_one('.lsqb-passage-content')
  passage_html=str(passage) if passage else None; passage_text=' '.join(passage.stripped_strings) if passage else None
  choices=[]
  for c in r.get('choices') or []:
   cs=BeautifulSoup(c.get('html') or '', 'html.parser')
   for el in cs.select('.ld-quiz-question-item__status,.wpProQuiz_response'):el.decompose()
   choices.append({'index':c.get('index'),'text':' '.join(cs.stripped_strings),'html':str(cs),'correct_if_explicitly_marked':c.get('correct_if_explicitly_marked')})
  key=(re.sub(r'\s+',' ',r.get('question_text','').casefold()).strip(),tuple(re.sub(r'\s+',' ',c['text'].casefold()).strip() for c in choices))
  digest=hashlib.sha256(repr(key).encode()).hexdigest(); groups[digest].append(r['id'])
  answer=r.get('correct_option_indexes'); rec={'question_id':r['id'],'source_url':u,'source_domain':'bbplus.plus','subject':subject,'category':None,'subcategory':None,'difficulty':None,'question_type':r.get('question_type'),'question_text':r.get('question_text'),'question_html':r.get('question_html'),'passage_text':passage_text,'passage_html':passage_html,'answer_choices':choices,'correct_answer':answer,'answer_verified':bool(answer),'answer_source':u if answer else None,'explanation':'\n'.join(r.get('explanations') or []) or None,'image_references':r.get('media_urls') or [],'local_asset_paths':[str(OUT/'assets'/Path(v).name) for k,v in assets.items() if k in (r.get('media_urls') or []) and (OUT/'assets'/Path(v).name).exists()],'equations':None,'test_id':m[3] if m else None,'test_name':m[3].replace('-',' ') if m else None,'test_year':year,'test_month':month,'test_region':'international' if 'intl' in path else None,'test_form':form[1].upper() if form else None,'module_number':int(mod[1]) if mod else None,'question_number':r.get('number'),'content_rights_status':r.get('rights_status'),'extraction_timestamp':None,'original_record':r}
  records.append(rec); tests[u].append(rec['question_id'])
 with (OUT/'questions.jsonl').open('w',encoding='utf-8') as f:
  for r in records:f.write(json.dumps(r,ensure_ascii=False)+'\n')
 dump('questions.json',records)
 with (OUT/'questions.csv').open('w',newline='',encoding='utf-8') as f:
  cols=['question_id','source_url','subject','question_text','passage_text','correct_answer','answer_verified','test_id','module_number','question_number']; w=csv.DictWriter(f,cols);w.writeheader();w.writerows({k:r.get(k) for k in cols} for r in records)
 dump('tests.json',[{'source_url':u,'question_ids':ids,'count':len(ids)} for u,ids in tests.items()]);dump('categories.json',[])
 discovered=json.loads((ROOT/'bbplus_all'/'discovered_quiz_urls.json').read_text()); known={r['source_url'] for r in records}
 dump('source_manifest.json',{'saved_record_source_urls':sorted(known),'historical_discovered_quiz_urls':discovered,'live_discovery_not_claimed':True})
 dup=[{'text_and_options_hash':k,'record_ids':v} for k,v in groups.items() if len(v)>1];dump('duplicates_report.json',{'exact_text_option_groups':dup,'record_count':len(records),'distinct_text_option_hashes':len(groups),'verified_unique_questions':None})
 coverage={'historical_advertised_items':7162,'extracted_records':len(records),'unique_record_ids':len({r['question_id'] for r in records}),'source_modules':len(tests),'question_text_complete':sum(bool(r['question_text']) for r in records),'choices_present':sum(bool(r['answer_choices']) for r in records),'passages_present':sum(bool(r['passage_text']) for r in records),'images_referenced_records':sum(bool(r['image_references']) for r in records),'verified_answers':sum(r['answer_verified'] for r in records),'explanations_present':sum(bool(r['explanation']) for r in records),'subject_counts':dict(Counter(r['subject'] for r in records)),'reconciliation_status':'not reconciled to authoritative inventory'};dump('coverage_report.json',coverage)
 missing=[{'source_url':u,'classification':'not verified from saved content; may be redirected, restricted, removed, parsing failure, or network error'} for u in discovered if u not in known];dump('missing_content_report.json',{'urls_without_saved_records':missing,'owner_request':'Provide a sanitized, content-only export with question IDs, rights status, rich stems/passages/options, explicit answers/explanations, asset mapping and test/category relationships; exclude accounts, credentials, payments and customer data.'})
 dump('answer_key_report.json',{'verified_answer_records':coverage['verified_answers'],'missing_answer_records':len(records)-coverage['verified_answers'],'owner_request':'Provide explicit answer-key export with stable question IDs, source, explanations and rights confirmation.'})
 (OUT/'extraction_summary.md').write_text(f"# BBPlus recovery summary\n\nLocal-only normalized export: {len(records)} records across {len(tests)} modules; {coverage['verified_answers']} verified answers. Historical 7,162 listing is not reconciled. Original JSONL is unchanged. {len(missing)} discovered URLs have no saved records; their precise status needs a read-only page report or owner export.\n\nOriginal source SHA-256: {hashlib.sha256(SRC.read_bytes()).hexdigest()}\n",encoding='utf-8')
 print(json.dumps(coverage,indent=2))
if __name__=='__main__':build()
