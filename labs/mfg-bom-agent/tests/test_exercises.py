"""수강생 과제 입력이 읽히고, 답변 검사 과제(Ch7-2)는 완성본에서 통과하는지 확인한다.

Ch2-2 · Ch5-1 과제는 처음 상태에서 일부러 실패하도록 만든 과제라 여기서 통과를 기대하지 않는다.
"""

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "exercise.py"


def load():
    spec = importlib.util.spec_from_file_location("exercise", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_exercise_inputs_load_and_answer_check_passes():
    ex = load()
    assert set(ex.EXERCISES) == {"ch2_2_pack", "ch5_1_link", "ch7_2_answer"}
    assert ex.ch7_2_answer(ex.EXERCISES["ch7_2_answer"]) is True
