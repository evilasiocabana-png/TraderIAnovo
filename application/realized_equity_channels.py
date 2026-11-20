"""Pure causal channel geometry shared by reports and the explicit M7 policy."""
import math
from statistics import median


def analyze_equity_channels(results, window=12, confirmations=3):
    if window not in (8, 12, 18) or confirmations not in (2, 3):
        raise ValueError("Parametros de estudo invalidos")
    equity = [0.0]
    for row in results:
        value = float(row["net"])
        if not math.isfinite(value):
            raise ValueError("Resultado nao finito")
        equity.append(equity[-1] + value)

    def fit(end):
        start = end - window + 1
        values = equity[start:end + 1]
        slope = median((values[j] - values[i]) / (j - i)
                       for i in range(window) for j in range(i + 1, window))
        intercept = median(value - slope * (start + i) for i, value in enumerate(values))
        residuals = [value - intercept - slope * (start + i) for i, value in enumerate(values)]
        scale = median(abs(b - a) for a, b in zip(values, values[1:]))
        margin = max(1.0, .25 * scale)
        trend = "Alta" if slope * (window - 1) > scale else "Baixa" if slope * (window - 1) < -scale else "Lateral"
        return dict(anchor=end, slope=slope, intercept=intercept,
                    lower=min(residuals) - margin, upper=max(residuals) + margin, trend=trend)

    if len(results) < window:
        return dict(segments=[], observations=[], events=[], trend="Sem amostra", consecutive=0)
    channel = fit(window)
    segments, observations, events = [], [], []
    previous_side, consecutive = "", 0
    for i in range(window + 1, len(equity)):
        center = channel["intercept"] + channel["slope"] * i
        lower, upper = center + channel["lower"], center + channel["upper"]
        side = "Acima" if equity[i] > upper else "Abaixo" if equity[i] < lower else "Dentro"
        consecutive = consecutive + 1 if side == previous_side and side != "Dentro" else 1 if side != "Dentro" else 0
        previous_side = side
        observations.append(dict(operation=i, net=float(results[i-1]["net"]), equity=equity[i],
                                 lower=lower, upper=upper, side=side, consecutive=consecutive,
                                 anchor=channel["anchor"], trend=channel["trend"]))
        if consecutive == confirmations:
            segments.append({**channel, "end":i})
            old = channel
            channel = fit(i)
            events.append(dict(operation=i, equity=equity[i], side=side,
                               previous=old["trend"], current=channel["trend"]))
            consecutive, previous_side = 0, ""
    segments.append({**channel, "end":len(results)})
    return dict(segments=segments, observations=observations, events=events,
                trend=channel["trend"], consecutive=consecutive)


def channel_plot_rows(study, first, last, max_channels=None):
    """Clip for display only; channel calibration always uses the full prefix."""
    rows = []
    visible = [s for s in study["segments"]
               if min(last, s["end"]) > max(first - 1, s["anchor"])]
    if max_channels is not None:
        visible = visible[-max_channels:]
    for index, segment in enumerate(visible):
        start, end = max(first - 1, segment["anchor"]), min(last, segment["end"])
        if end <= start:
            continue
        for edge in ("lower", "upper"):
            rows.append(dict(start=start, end=end, edge=edge, trend=segment["trend"],
                             begin=segment["intercept"] + segment["slope"] * start + segment[edge],
                             finish=segment["intercept"] + segment["slope"] * end + segment[edge],
                             anchor=segment["anchor"],
                             opacity=1.0 if index == len(visible)-1 else .35))
    return rows
