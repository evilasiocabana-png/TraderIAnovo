"""Registro oficial de regras de validacao quantitativa."""

from dataclasses import dataclass, field

from research.validation.validation_rule import ValidationRule


DEFAULT_VALIDATION_RULES: tuple[ValidationRule, ...] = (
    ValidationRule(
        rule_id="minimum_trades",
        name="Minimum Trades",
        description="Exige quantidade minima de trades para pesquisa.",
        severity="HIGH",
        threshold=30.0,
        enabled=True,
        metadata={"category": "sample"},
    ),
    ValidationRule(
        rule_id="maximum_drawdown",
        name="Maximum Drawdown",
        description="Limita drawdown maximo aceitavel.",
        severity="HIGH",
        threshold=100.0,
        enabled=True,
        metadata={"category": "risk"},
    ),
    ValidationRule(
        rule_id="minimum_profit_factor",
        name="Minimum Profit Factor",
        description="Exige profit factor minimo para validacao.",
        severity="HIGH",
        threshold=1.2,
        enabled=True,
        metadata={"category": "profitability"},
    ),
    ValidationRule(
        rule_id="minimum_win_rate",
        name="Minimum Win Rate",
        description="Exige taxa minima de acerto.",
        severity="MEDIUM",
        threshold=0.4,
        enabled=True,
        metadata={"category": "consistency"},
    ),
    ValidationRule(
        rule_id="maximum_outlier_dependency",
        name="Maximum Outlier Dependency",
        description="Limita dependencia de operacoes extremas.",
        severity="MEDIUM",
        threshold=30.0,
        enabled=True,
        metadata={"category": "robustness"},
    ),
)


@dataclass
class ValidationRuleRegistry:
    """Gerencia regras declarativas de validacao em memoria."""

    _rules: dict[str, ValidationRule] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        for rule in DEFAULT_VALIDATION_RULES:
            self.register(rule)

    def register(self, rule: ValidationRule) -> ValidationRule:
        """Registra ou substitui uma regra de validacao."""
        self._rules[rule.rule_id] = rule
        return rule

    def unregister(self, rule_id: str) -> bool:
        """Remove uma regra registrada quando existir."""
        if rule_id not in self._rules:
            return False
        del self._rules[rule_id]
        return True

    def get(self, rule_id: str) -> ValidationRule | None:
        """Retorna uma regra pelo identificador."""
        return self._rules.get(rule_id)

    def list(self) -> tuple[ValidationRule, ...]:
        """Lista regras registradas."""
        return tuple(self._rules.values())

    def exists(self, rule_id: str) -> bool:
        """Indica se uma regra esta registrada."""
        return rule_id in self._rules
