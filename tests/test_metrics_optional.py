import pytest
pytest.importorskip('sklearn',reason='ML evaluation dependency not installed')
from voicescope.evaluate import metrics


def test_metrics_score_orientation_and_ties():
    perfect=metrics([0,0,1,1],[.1,.2,.8,.9],.5)
    assert perfect['eer_interpolated']==0
    assert perfect['confusion_matrix_real_fake']==[[2,0],[0,2]]
    tied=metrics([0,1],[.5,.5],.5)
    assert tied['eer_interpolated']==pytest.approx(.5)
