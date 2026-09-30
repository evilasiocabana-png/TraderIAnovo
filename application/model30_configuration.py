"""Single persisted M30 entry permission, shared by execution and UI."""
from application.learning_store import LearningStore, now


def enabled(store=None):
    store = store or LearningStore()
    if not store.path.exists():
        return False
    with store.connect() as db:
        row = db.execute("SELECT value FROM metadata WHERE key='m30_enabled'").fetchone()
    return bool(row and row[0] == "true")


def set_enabled(value: bool, store=None):
    from application.learning_policy import tables, journal
    store = store or LearningStore()
    with store.connect() as db:
        tables(db)
        db.execute("INSERT OR REPLACE INTO metadata VALUES ('m30_enabled',?)", ("true" if value else "false",))
        journal(db, "CONFIGURACAO", "M30",
                "Novas entradas independentes M30 Demo habilitadas." if value else
                "Novas entradas M30 Demo desabilitadas; posicoes abertas preservadas.", {}, now())
