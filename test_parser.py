from extract_bbplus import extract_quiz, discovered_links

SAMPLE_HTML = '''<!doctype html><html><head><title>Test</title></head><body>
<a href="/courses/test/lessons/part/quizzes/module-1/">quiz</a>
<div class="wpProQuiz_question"><div class="wpProQuiz_question_text"><p>A triangle has sides 3, 4, 5. Is it right?</p></div>
<ul class="wpProQuiz_questionList" data-question_id="55" data-type="single">
<li class="wpProQuiz_questionListItem"><label><input type="radio">No</label></li>
<li class="wpProQuiz_questionListItem" data-correct="true"><label><input type="radio">Yes</label></li>
</ul><div class="wpProQuiz_response"><div class="wpProQuiz_correct">Correct</div></div></div>
</body></html>'''


def test_extraction():
    url = "https://bbplus.plus/courses/test/lessons/part/quizzes/module-1/"
    questions = extract_quiz(SAMPLE_HTML, url)
    assert len(questions) == 1
    assert questions[0]["question_text"].startswith("A triangle")
    assert len(questions[0]["choices"]) == 2
    assert questions[0]["correct_option_indexes"] == [1]
    assert questions[0]["explanations"] == []
    quizzes, _ = discovered_links(SAMPLE_HTML, url)
    assert url in quizzes


if __name__ == "__main__":
    test_extraction()
    print("Offline parser test: PASS")
