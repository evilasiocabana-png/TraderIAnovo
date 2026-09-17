"""Descriptive, causal equity structure. Never imported by order execution."""
import math
from statistics import median


def analyze_equity_structure(results, sensitivity=1.0):
    """Confirm extrema only after an opposite move >= sensitivity * rolling
    median absolute closed result (last 20, all already observed). Labels begin
    at confirmation, never retroactively at the extreme. No price forecast.
    """
    if not math.isfinite(sensitivity) or sensitivity <= 0:
        raise ValueError("Sensibilidade deve ser positiva")
    equity=0.0
    extreme=0.0
    extreme_index=0
    direction=0
    state="Formacao"
    confirmed_regime=None
    sizes=[]
    tops=[]
    bottoms=[]
    pivots=[]
    points=[dict(operation=0,equity=0.0,net=0.0,letter="",state=state,time="Inicio")]
    segments=[]
    transitions=[]
    for i,result in enumerate(results,1):
        net=float(result["net"])
        if not math.isfinite(net):raise ValueError("Resultado nao finito")
        equity=round(equity+net,2)
        if net:sizes.append(abs(net))
        threshold=max(.01, sensitivity*median(sizes[-20:])) if sizes else .01
        pivot=None
        if direction==0:
            if abs(equity-extreme)>=threshold:
                direction=1 if equity>extreme else -1
                extreme,extreme_index=equity,i
        elif direction==1:
            if equity>=extreme:
                extreme,extreme_index=equity,i
            elif extreme-equity>=threshold:
                pivot=dict(operation=extreme_index,equity=extreme,kind="Topo",confirmed=i)
                tops.append(pivot);direction=-1;extreme,extreme_index=equity,i
        else:
            if equity<=extreme:
                extreme,extreme_index=equity,i
            elif equity-extreme>=threshold:
                pivot=dict(operation=extreme_index,equity=extreme,kind="Fundo",confirmed=i)
                bottoms.append(pivot);direction=1;extreme,extreme_index=equity,i
        if pivot:
            pivots.append(pivot)
            if len(tops)>=2 and len(bottoms)>=2:
                higher=tops[-1]["equity"]>tops[-2]["equity"] and bottoms[-1]["equity"]>bottoms[-2]["equity"]
                lower=tops[-1]["equity"]<tops[-2]["equity"] and bottoms[-1]["equity"]<bottoms[-2]["equity"]
                state="Alta" if higher else "Baixa" if lower else "Transicao"
                if state in ("Alta","Baixa"):
                    if confirmed_regime and confirmed_regime!=state:
                        transitions.append(dict(operation=i,previous=confirmed_regime,current=state))
                    confirmed_regime=state
        # Breach of the last structural boundary marks a possible reversal;
        # only two confirmed tops AND bottoms can confirm the opposite regime.
        if state=="Alta" and bottoms and equity<bottoms[-1]["equity"]:
            state="Transicao"
        elif state=="Baixa" and tops and equity>tops[-1]["equity"]:
            state="Transicao"
        letter="G" if net>0 else "P" if net<0 else "E"
        points.append(dict(operation=i,equity=equity,net=net,letter=letter,state=state,time=result.get("time", "")))
        if not segments or segments[-1]["state"]!=state:
            segments.append(dict(start=i,end=i,state=state,letters=letter,net=net))
        else:
            seg=segments[-1];seg["end"]=i;seg["letters"]+=" "+letter;seg["net"]=round(seg["net"]+net,2)
    return dict(points=points,pivots=pivots,segments=segments,transitions=transitions,state=state,net=equity)
