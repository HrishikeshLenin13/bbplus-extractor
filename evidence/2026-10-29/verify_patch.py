import importlib.util,sys
from pathlib import Path
p=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('m',p/'MODIFIED_FILE.py');m=importlib.util.module_from_spec(spec);sys.modules['m']=m;spec.loader.exec_module(m)
h='<div class="wpProQuiz_question"><div class="wpProQuiz_question_text"><div class="lsqb-passage-content">Passage</div>Question?</div><ul class="wpProQuiz_questionList"><li class="wpProQuiz_questionListItem"><label>Choice<span class="ld-quiz-question-item__status">Correct answer</span></label></li></ul></div>'
r=m.extract_quiz(h,'https://bbplus.plus/courses/test/quizzes/q/')[0]
assert r['choices'][0]['text']=='Choice' and r['passage_text']=='Passage'
print('PASS: choice status excluded; passage preserved')
