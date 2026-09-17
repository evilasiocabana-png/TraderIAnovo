from scripts.study_m23_sequences_all import describe


def test_runs_and_alternating_net():
    rows = [dict(ticket=i, exit=i, net=x) for i,x in enumerate([-1,-2,5,-3,6,-2,4])]
    s = describe(rows)
    assert s['count'] == 7 and s['wins'] == 3
    assert s['max_loss_run'] == 2
    assert s['net'] == 7
    assert s['after_losses']['2'] == dict(samples=1, next_wins=1, next_net=5)
    assert s['alternating_blocks'][0]['net'] == 8


def test_zero_breaks_loss_sequence_and_empty_is_unknown():
    rows = [dict(ticket=i, exit=i, net=x) for i,x in enumerate([-1,0,-1])]
    assert describe(rows)['max_loss_run'] == 1
    assert describe([])['win_rate'] is None
