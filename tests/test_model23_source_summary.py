from types import SimpleNamespace
from application.model23_source_summary import summarize_m23_sources


def row(ticket,source,profit,commission=0,**extra):
    return SimpleNamespace(mt5_ticket=ticket,operational_model=f"MODELO_23_BASKET_ACCUMULATOR_SOURCE_M{source}",
        mt5_found=True,operation_status="FECHADA/HISTORICO",mt5_realized_profit=profit,
        mt5_commission=commission,mt5_swap=0,mt5_fee=0,**extra)


def test_sources_counts_costs_duplicates_and_copy_kept_separate():
    rows=[row(1,7,100,-2),row(2,7,-50,-1),row(3,29,20,-1),row(4,8,1,-2),row(5,18,0)]
    rows.append(rows[0])
    opened=row(6,7,500);opened.operation_status="ABERTA";rows.append(opened)
    result=summarize_m23_sources(rows)
    by={r['Fonte do sinal']:r for r in result}
    assert by['M7']['Sequencia completa']=='G P'
    assert by['M29']['Sequencia completa']=='G'
    assert by['M8']['Sequencia completa']=='P'
    assert by['M18']['Sequencia completa']=='E'
    assert all(set(r)=={'Fonte do sinal','Sequencia completa','Saldo liquido (US$)'} for r in result)
    recent=summarize_m23_sources([row(i,7,1 if i%2 else -1) for i in range(1,10)])
    assert recent[0]['Sequencia completa']=='G P G P G P G P G'


def test_unknown_source_retained_and_unconfirmed_excluded():
    unknown=row(1,7,-3);unknown.operational_model="MODELO_23_BASKET_ACCUMULATOR"
    missing=row(2,7,12);missing.mt5_found=False
    result=summarize_m23_sources([unknown,missing])
    assert result[0]['Fonte do sinal']=='Origem nao identificada'
    assert len(result)==1 and result[0]['Sequencia completa']=='P'
    assert summarize_m23_sources([])==[]


def test_active_sources_only_all_results_and_net_balance():
    rows=[row(i,7,10 if i%2 else -5,commission=-1) for i in range(1,13)]
    rows += [row(13,3,1000),row(14,29,-20)]
    result=summarize_m23_sources(rows,{'M7','M8','M29'})
    by={r['Fonte do sinal']:r for r in result}
    assert set(by)=={'M7','M8','M29'}
    assert len(by['M7']['Sequencia completa'].split())==12
    assert by['M7']['Saldo liquido (US$)']==18
    assert by['M8']['Sequencia completa']=='Sem encerramentos'
    assert by['M8']['Saldo liquido (US$)']==0
    assert by['M29']['Saldo liquido (US$)']==-20
