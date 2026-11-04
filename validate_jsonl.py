"""Offline structural preflight for local extracted question records; no content downloads."""
import argparse,json
from pathlib import Path

def validate_jsonl(path):
    errors=[];seen=set();records=0
    with Path(path).open(encoding='utf-8-sig') as source:
        for number,line in enumerate(source,1):
            if not line.strip():continue
            records+=1
            try:
                row=json.loads(line)
                if not isinstance(row,dict):raise ValueError('record must be an object')
                identity=row.get('id')
                if not isinstance(identity,str) or not identity.strip():raise ValueError('id must be a nonempty string')
                if identity in seen:raise ValueError('duplicate id')
                seen.add(identity)
                choices=row.get('choices',[])
                if not isinstance(choices,list):raise ValueError('choices must be a list')
                answers=row.get('correct_option_indexes')
                if answers is not None:
                    if not isinstance(answers,list) or any(type(index) is not int or index<0 or index>=len(choices) for index in answers):raise ValueError('answer indexes must reference known choices')
                    if len(set(answers))!=len(answers):raise ValueError('answer indexes must be unique')
            except (ValueError,TypeError) as error:
                errors.append({'line':number,'message':str(error)})
    return {'ok':not errors,'records':records,'errors':errors}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('path',type=Path);args=parser.parse_args(argv)
    try:report=validate_jsonl(args.path)
    except (OSError,UnicodeError) as error:report={'ok':False,'records':0,'errors':[{'message':str(error)}]}
    print(json.dumps(report));return 0 if report['ok'] else 1

if __name__=='__main__':raise SystemExit(main())
