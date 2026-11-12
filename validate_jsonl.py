"""Offline structural preflight for local extracted question records; no content downloads."""
import argparse,json,sys
from pathlib import Path

def validate_jsonl(path, *, max_errors=None):
    """Validate a UTF-8 file without modifying it."""
    with Path(path).open(encoding='utf-8-sig') as source:
        return validate_stream(source, max_errors=max_errors)

def validate_stream(source, *, max_errors=None):
    """Scan an iterable of text lines, retaining only the requested diagnostics."""
    if max_errors is not None and (type(max_errors) is not int or max_errors < 0):
        raise ValueError('max_errors must be a nonnegative integer')
    errors=[];seen=set();records=0;error_count=0
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
            error_count+=1
            if max_errors is None or len(errors)<max_errors:
                errors.append({'line':number,'message':str(error)})
    report={'ok':error_count==0,'records':records,'errors':errors}
    if max_errors is not None:
        report['error_count']=error_count
    return report

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path',help='UTF-8 JSONL file, or - to read standard input')
    parser.add_argument('--max-errors',type=int,help='cap stored record diagnostics; 0 counts only')
    args=parser.parse_args(argv)
    if args.max_errors is not None and args.max_errors<0:
        parser.error('--max-errors must be nonnegative')
    try:
        if args.path=='-':
            sys.stdin.reconfigure(encoding='utf-8-sig', errors='strict')
            report=validate_stream(sys.stdin,max_errors=args.max_errors)
        else:
            report=validate_jsonl(args.path,max_errors=args.max_errors)
    except (OSError,UnicodeError) as error:
        report={'ok':False,'records':0,'errors':[{'message':str(error)}]}
    print(json.dumps(report));return 0 if report['ok'] else 1

if __name__=='__main__':raise SystemExit(main())
