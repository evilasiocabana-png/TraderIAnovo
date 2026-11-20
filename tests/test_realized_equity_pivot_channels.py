import random
import pytest
from application.realized_equity_pivot_channels import analyze_pivot_channels
from application.realized_equity_channels import channel_plot_rows


def run(values):
    return analyze_pivot_channels([dict(net=v) for v in values])


def test_parallel_causal_and_confirmed_pivots_only():
    rng = random.Random(17)
    values = [100,-100,200,-100,200,-100] + [rng.choice([-250,-100,0,100,400]) for _ in range(80)]
    full = run(values)
    for n in range(len(values)+1):
        partial = run(values[:n])
        assert partial['events'] == [e for e in full['events'] if e['operation'] <= n]
        assert partial['observations'] == [o for o in full['observations'] if o['operation'] <= n]
        for segment in partial['segments']:
            assert all(p['confirmed'] <= segment['anchor'] for p in segment['pivots'])
    edges = channel_plot_rows(full, 1, len(values))
    for lower, upper in zip(edges[::2], edges[1::2]):
        assert upper['begin']-lower['begin'] == pytest.approx(upper['finish']-lower['finish'])


def test_flat_closes_and_unchanged_geometry_do_not_erase_count():
    result = run([100,-100,200,-100,200,-100,0,0,0])
    assert [o['consecutive'] for o in result['observations'][-3:]] == [1,2,3]
    assert len(result['events']) == 1
    assert len(result['segments']) == 1
    assert result['events'][0]['side'] == 'Abaixo'


def test_inside_resets_and_exact_touch_is_not_break():
    result = run([100,-100,200,-100,200,-100,-100,200,-100])
    assert [o['side'] for o in result['observations']] == ['Dentro','Abaixo','Dentro','Abaixo']
    assert not result['events']


def test_no_channel_without_two_pairs_and_reject_invalid():
    assert not run([10]*50)['segments']
    assert not run([0]*50)['segments']
    for value in [float('nan'),float('inf')]:
        with pytest.raises(ValueError):run([value])
