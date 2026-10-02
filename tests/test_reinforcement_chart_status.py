from application.reinforcement_chart_status import chart_status
from tests.test_source_channel_gate import deals


def payload(values):
    rows=[]
    for i,n in enumerate(values,1):
        pair=deals(i);pair[0].update(commission=0,fee=0);pair[1].update(profit=n,commission=0,fee=0,swap=0)
        rows.extend(pair)
    return dict(ok=True,account=dict(trade_mode=0,margin_mode=2),rows=rows)


def test_falling_suspends_and_rising_permits_without_claiming_execution():
    assert 'SUSPENSO' in chart_status(payload([-100,100,-200,100,-200,100]),'M7')[0]
    line=chart_status(payload([100,-100,200,-100,200,-100]),'M7')[0]
    assert 'SUSPENSO' in line and 'M29 e M30' in line


def test_other_asset_and_source_are_isolated():
    data=payload([-100,100,-200,100,-200,100])
    assert 'SUSPENSO' in chart_status(data,'M18')[0]
    line=chart_status(data,'M7',['BTCUSD'])[0]
    assert 'M29' not in line and 'PERMITIDO' in line
    assert 'Sem reforco' in chart_status(data,'M28')[0]


def test_failure_is_not_reported_as_permission():
    assert 'indisponivel' in chart_status({},'M7')[0]
    data=payload([10]);data['rows'][1]['volume']=.05
    assert 'INDISPONIVEL' in chart_status(data,'M7')[0]


def test_trading_text_distinguishes_executed_pending_and_legacy():
    from types import SimpleNamespace as NS
    from application.reinforcement_chart_status import trading_reinforcement_text
    from application.source_channel_gate import POLICY
    def row(model,status,policy=POLICY,found=True):
        return NS(operational_model=model,operation_status=status,mt5_found=found,mt5_ticket=123,symbol='XAUUSD',plan_snapshot=dict(stop_management_parameters=dict(reinforcement_policy=policy,reinforcement_source=18)))
    result=trading_reinforcement_text([
        row('MODELO_23_BASKET_ACCUMULATOR_SOURCE_M29','ABERTA'),
        row('MODELO_30_ADAPTIVE_SOURCE_M18','ORDEM_ABERTA'),
        row('MODELO_30_ADAPTIVE_SOURCE_M18','ABERTA','legacy'),
        row('MODELO_30_ADAPTIVE_SOURCE_M18','ABERTA',found=False),
        row('MODELO_23_BASKET_ACCUMULATOR_SOURCE_M18','ABERTA')])
    assert 'M29 executado pelo M23' in result[0] and 'M30' not in result[0]
    assert 'pendente' in result[1] and 'M30' in result[1]
    assert 'nenhum confirmado' in trading_reinforcement_text([])[0]
