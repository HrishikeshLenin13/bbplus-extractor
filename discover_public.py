#!/usr/bin/env python3
"""Bounded read-only inspection of three known public catalog pages."""
import json
from pathlib import Path
from bs4 import BeautifulSoup
from extract_bbplus import Downloader,INDEXES,discovered_links
out=Path(__file__).resolve().parent/'output'; out.mkdir(exist_ok=True)
dl=Downloader(2.0); result=[]
for u in INDEXES:
 status,data,final=dl.get(u); item={'url':u,'status':status,'final_url':final}
 if status=='ok' and data:
  soup=BeautifulSoup(data,'html.parser'); qs,cs=discovered_links(data.decode('utf-8','replace'),final)
  item.update(title=soup.title.get_text(' ',strip=True) if soup.title else None,quiz_links=sorted(qs),course_links=sorted(cs),page_next_links=[a.get('href') for a in soup.select('a[rel=next],a.next,a.page-numbers.next')])
 result.append(item)
 if status in ('rate_limited_STOP','login_required_or_forbidden'):break
(out/'source_discovery_report.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
print([(x['status'],len(x.get('quiz_links',[])),len(x.get('course_links',[]))) for x in result])
