import json, hashlib
from pathlib import Path
from extract_bbplus import extract_quiz
from build_database import build
p=Path(__file__).resolve().parent
assert hashlib.sha256((p/'bbplus_all/questions.jsonl').read_bytes()).hexdigest()=='19e614cd0fa4fc359cb40890a1c2315f6cdcba2dac995ae50dc3735a53c8cf4b'
assert len([x for x in (p/'bbplus_all/questions.jsonl').read_text().splitlines() if x])==196
h='<div class="wpProQuiz_question"><div class="wpProQuiz_question_text"><div class="lsqb-passage-content">Passage</div>Question?</div><ul class="wpProQuiz_questionList"><li class="wpProQuiz_questionListItem"><label>Choice<span class="ld-quiz-question-item__status">Correct answer</span></label></li></ul></div>'
r=extract_quiz(h,'https://bbplus.plus/courses/test/quizzes/q/')[0]
assert r['choices'][0]['text']=='Choice'
assert r['passage_text']=='Passage'
build(); out=json.loads((p/'output/questions.json').read_text());assert len(out)==196 and not any(x['answer_verified'] for x in out)
print('Recovery tests: PASS; 196 preserved; status labels excluded; 0 invented answers')
