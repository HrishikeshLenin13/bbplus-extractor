import json,tempfile,unittest
from pathlib import Path
from validate_jsonl import validate_jsonl
class JsonlPreflight(unittest.TestCase):
    def test_bom_empty_lines_duplicates_and_invalid_answers(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'questions.jsonl';rows=[{'id':'one','choices':[{'text':'A'}],'correct_option_indexes':[0]},{'id':'two','correct_option_indexes':None}]
            path.write_text('\ufeff'+json.dumps(rows[0])+'\n\n'+json.dumps(rows[1])+'\n',encoding='utf-8');before=path.read_bytes();self.assertTrue(validate_jsonl(path)['ok']);self.assertEqual(path.read_bytes(),before)
            path.write_text(json.dumps(rows[0])+'\n'+json.dumps(rows[0])+'\n'+json.dumps({'id':'three','choices':[],'correct_option_indexes':[0]})+'\n{bad',encoding='utf-8');result=validate_jsonl(path);self.assertFalse(result['ok']);self.assertEqual([e['line'] for e in result['errors']],[2,3,4]);self.assertEqual(result['records'],4)


    def test_cap_keeps_counting_and_preserves_failure_exit(self):
        import contextlib
        import io
        from validate_jsonl import main

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'questions.jsonl'
            path.write_text('{}\n{"id":"ok"}\n{"id":"ok"}\n{bad\n', encoding='utf-8')
            report = validate_jsonl(path, max_errors=1)
            self.assertFalse(report['ok'])
            self.assertEqual(report['records'], 4)
            self.assertEqual(report['error_count'], 3)
            self.assertEqual([entry['line'] for entry in report['errors']], [1])
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main([str(path), '--max-errors', '0']), 1)
            self.assertEqual(json.loads(output.getvalue()), {
                'ok': False, 'records': 4, 'errors': [], 'error_count': 3,
            })
            with self.assertRaises(ValueError):
                validate_jsonl(path, max_errors=-1)
