import json,tempfile,unittest
from pathlib import Path
from validate_jsonl import validate_jsonl
class JsonlPreflight(unittest.TestCase):
    def test_bom_empty_lines_duplicates_and_invalid_answers(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'questions.jsonl';rows=[{'id':'one','choices':[{'text':'A'}],'correct_option_indexes':[0]},{'id':'two','correct_option_indexes':None}]
            path.write_text('\ufeff'+json.dumps(rows[0])+'\n\n'+json.dumps(rows[1])+'\n',encoding='utf-8');before=path.read_bytes();self.assertTrue(validate_jsonl(path)['ok']);self.assertEqual(path.read_bytes(),before)
            path.write_text(json.dumps(rows[0])+'\n'+json.dumps(rows[0])+'\n'+json.dumps({'id':'three','choices':[],'correct_option_indexes':[0]})+'\n{bad',encoding='utf-8');result=validate_jsonl(path);self.assertFalse(result['ok']);self.assertEqual([e['line'] for e in result['errors']],[2,3,4]);self.assertEqual(result['records'],4)
