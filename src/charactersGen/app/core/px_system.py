"""Sistema di gestione dei Punti Esperienza (PX) del GDR v0.8.

I PX vengono spesi per acquistare:
- Gradi nelle abilità
- Apprendimenti

Nota: [PLACEHOLDER] il costo per aumentare un grado abilità deve ancora essere definito.
Per ora si usa una stima basata sul numero di grado (grado × 500 PX).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.data.learnings import LEARNINGS, get_learning
from app.schemas import AbilityGrade, Learning


# Costo stimato per grado abilità (da rivedere con il manuale)
# TODO: verificare con le regole ufficiali il costo esatto per grado abilità
_ABILITY_GRADE_COST_PER_LEVEL = 500


@dataclass
class PXSystem:
    """Gestisce i PX durante la creazione del personaggio."""

    px_total: int
    px_spent: int = field(default=0)
    log: list[str] = field(default_factory=list)

    @property
    def px_remaining(self) -> int:
        """PX non ancora spesi."""
        return self.px_total - self.px_spent

    def can_afford(self, cost: int) -> bool:
        """Verifica se ci sono abbastanza PX.

        Args:
            cost: costo da verificare.

        Returns:
            True se i PX rimanenti sono sufficienti.
        """
        return self.px_remaining >= cost

    def spend(self, cost: int, description: str = "") -> bool:
        """Spende PX se disponibili.

        Args:
            cost: PX da spendere.
            description: descrizione della spesa (per il log).

        Returns:
            True se la spesa è andata a buon fine, False altrimenti.
        """
        if not self.can_afford(cost):
            return False
        self.px_spent += cost
        if description:
            self.log.append(f"-{cost} PX: {description}")
        return True

    def refund(self, cost: int, description: str = "") -> None:
        """Rimborsa PX (es. per annullare un acquisto).

        Args:
            cost: PX da rimborsare.
            description: descrizione del rimborso.
        """
        self.px_spent = max(0, self.px_spent - cost)
        if description:
            self.log.append(f"+{cost} PX (rimborso): {description}")

    def buy_learning(
        self,
        learning_name: str,
        owned_learnings: list[str],
    ) -> tuple[bool, str]:
        """Acquista un apprendimento.

        Args:
            learning_name: nome dell'apprendimento.
            owned_learnings: lista degli apprendimenti già posseduti (modificata in-place se successo).

        Returns:
            (successo, messaggio di errore o conferma).
        """
        learning = get_learning(learning_name)
        if learning is None:
            return False, f"Apprendimento '{learning_name}' non trovato."

        if learning_name in owned_learnings:
            return False, f"Hai già l'apprendimento '{learning_name}'."

        # Verifica prerequisiti
        for prereq in learning.prerequisites:
            if prereq not in owned_learnings:
                return False, f"Prerequisito mancante: '{prereq}'."

        if not self.can_afford(learning.cost):
            return False, (
                f"PX insufficienti: {learning.cost} richiesti, {self.px_remaining} disponibili."
            )

        self.spend(learning.cost, f"Apprendimento: {learning_name}")
        owned_learnings.append(learning_name)
        return True, f"Apprendimento '{learning_name}' acquisito ({learning.cost} PX)."

    def buy_ability_grade(
        self,
        ability_name: str,
        abilities: list[AbilityGrade],
        max_grade: int,
    ) -> tuple[bool, str]:
        """Aumenta di 1 il grado in un'abilità.

        Il costo è: (grado_corrente + 1) × 500 PX (stima).

        Args:
            ability_name: nome dell'abilità.
            abilities: lista corrente delle abilità (modificata in-place se successo).
            max_grade: grado massimo consentito (= INT del personaggio).

        Returns:
            (successo, messaggio).
        """
        ability = next((a for a in abilities if a.name == ability_name), None)
        if ability is None:
            return False, f"Abilità '{ability_name}' non trovata."

        if ability.grades >= max_grade:
            return False, (
                f"'{ability_name}' ha già raggiunto il grado massimo ({max_grade})."
            )

        cost = (ability.grades + 1) * _ABILITY_GRADE_COST_PER_LEVEL
        if not self.can_afford(cost):
            return False, (
                f"PX insufficienti: {cost} richiesti per grado {ability.grades + 1}, "
                f"{self.px_remaining} disponibili."
            )

        self.spend(cost, f"Abilità: {ability_name} → grado {ability.grades + 1}")
        ability.grades += 1
        return True, f"'{ability_name}' ora a grado {ability.grades} (-{cost} PX)."

    def summary(self) -> str:
        """Riepilogo spesa PX.

        Returns:
            Stringa formattata con il riepilogo.
        """
        lines = [
            f"PX Totali:    {self.px_total}",
            f"PX Spesi:     {self.px_spent}",
            f"PX Rimanenti: {self.px_remaining}",
        ]
        if self.log:
            lines.append("\nDettaglio spese:")
            lines.extend(f"  {entry}" for entry in self.log)
        return "\n".join(lines)
