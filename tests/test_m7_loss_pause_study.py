from scripts.study_m7_loss_pause import simulate


def row(ticket, start, end, net):
    return dict(ticket=ticket, entry=start, exit=end, net=net)


def test_overlapping_entry_cannot_know_future_loss():
    result = simulate([row(1,1,5,-10), row(2,2,6,-20), row(3,7,8,-30)], 1, 1)
    assert result['taken'] == 2
    assert result['skipped_tickets'] == [3]
    assert result['net'] == -30


def test_recovery_gain_is_shadow_not_realized():
    result = simulate([row(1,1,2,-10), row(2,3,4,20), row(3,5,6,30)], 1, 1)
    assert result['net'] == 20
    assert result['missed_gains'] == 20
    assert result['resumes'] == 1


def test_two_wins_must_be_consecutive():
    rows = [row(i,2*i,2*i+1,n) for i,n in enumerate([-10,20,-5,20,20,30])]
    result = simulate(rows, 1, 2)
    assert result['taken'] == 2
    assert result['resumes'] == 1
    assert result['net'] == 20
