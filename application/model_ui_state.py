"""Shared presentation contract. Never decides signals or changes entry permissions."""
from dataclasses import dataclass
from domain.operational_model_policy import ACTIVE_OPERATIONAL_MODEL_NUMBERS, operational_model_number
from application.model30_configuration import enabled

REPORT_MODEL_NUMBERS = tuple(sorted((*ACTIVE_OPERATIONAL_MODEL_NUMBERS, 30)))
M30_DESCRIPTION = ("M30 independente: recebe sinais originais. M7 usa o canal dos encerramentos originais no M23: "
                   "abaixo do piso espelha, retorno ao canal de alta normaliza. Canal de baixa confirmado espelha.")
M30_HISTORY_DESCRIPTION = ("Somente operacoes encerradas identificadas pela politica atual de canal do M30, "
                          "dentro do periodo selecionado. Historico anterior excluido deste grafico.")


@dataclass(frozen=True)
class ModelUIState:
    active_labels: tuple[str, ...]
    m30_enabled: bool

    @property
    def summary(self):
        return " + ".join(self.active_labels) if len(self.active_labels) <= 3 else f"{len(self.active_labels)} MODELOS"

    @property
    def caption(self):
        return "Habilitados para novas entradas: " + (", ".join(self.active_labels) or "nenhum")


def model_ui_state(selections=(), *, store=None):
    active = enabled(store)
    labels = tuple(dict.fromkeys(f"M{n}" for value in selections
                                if (n := operational_model_number(value)) is not None))
    return ModelUIState(labels + (("M30",) if active else ()), active)


def m30_permission_text(active):
    return "M30: novas entradas independentes na Demo " + ("habilitadas." if active else "desabilitadas.")


def sync_persisted_widget(session, key, persisted):
    """Refresh stale UI after another tab changes storage; preserve unsaved local edits."""
    revision_key = key + "__persisted"
    if key not in session or session.get(revision_key) != persisted:
        session[key] = persisted
    session[revision_key] = persisted
