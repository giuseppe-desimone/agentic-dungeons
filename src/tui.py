"""Demo TUI: barra di tab cliccabile (mouse) e navigabile (tastiera).

Mostra i meccanismi base di una TUI moderna (stile Copilot CLI / Claude Code):
- un "canvas" di celle gestito dal framework (Textual)
- eventi mouse (click) e tastiera (Tab, Shift+Tab, F1/F2/F3)
- uno status bar che mostra l'ultimo evento ricevuto, per vedere
  in tempo reale come il terminale "parla" con l'app

Esecuzione:  .venv/bin/python app.py
"""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.events import Click, Key
from textual.message import Message
from textual.reactive import reactive
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Footer, Static


class TabBar(Widget):
    """Barra di tab: ogni tab è un widget con il proprio bounding box.

    Il framework (Textual) riceve gli eventi mouse dal terminale
    (sequenze escape SGR, attivate con \x1b[?1006h) e li converte
    in eventi Click con coordinate (x, y). Qui basta gestire
    on_click: il mapping coordinate->widget lo fa il layout.
    """

    DEFAULT_CSS = """
    TabBar {
        layout: horizontal;
        height: 1;            /* barra di tab a 1 riga */
        background: transparent;
    }
    .tab {
        width: auto;          /* altrimenti ogni tab "riempie" l'intera larghezza */
        height: 1;
        padding: 0 2;
        margin: 0 1;
        color: $text-muted;
        background: $surface; /* il "riquadro" è il rettangolo colorato */
    }
    .tab.-active {
        color: $text;
        background: $primary;
        text-style: bold;
    }
    """

    def __init__(self, tabs: list[str]) -> None:
        super().__init__()
        self.tabs = tabs
        self.active = 0

    def compose(self) -> ComposeResult:
        for i, name in enumerate(self.tabs):
            yield Static(f" {name} ", id=f"tab-{i}", classes="tab")

    def _refresh_styles(self) -> None:
        for i in range(len(self.tabs)):
            self.query_one(f"#tab-{i}", Static).set_class(i == self.active, "-active")

    def on_mount(self) -> None:
        self._refresh_styles()

    def set_active(self, index: int) -> None:
        """Aggiorna solo l'evidenziazione. Lo stato vero è nell'App:
        viene chiamato da App.show_tab() sia per click che per tastiera."""
        self.active = index % len(self.tabs)
        self._refresh_styles()

    def on_click(self, event: Click) -> None:
        # Il click arriva già "mappato" sul widget tab:
        # il framework ha convertito (col, row) del terminale
        # in coordinate del widget (event.widget).
        # Qui non aggiorniamo lo stato: notifichiamo l'App, che è
        # la sorgente di verità e deciderà cosa mostrare.
        for i in range(len(self.tabs)):
            if event.widget is not None and event.widget.id == f"tab-{i}":
                self.post_message(TabBar.TabSelected(i))
                break

    class TabSelected(Message):
        def __init__(self, index: int) -> None:
            super().__init__()
            self.index = index


class TabPanel(Static):
    """Pannello di contenuto di una tab."""

    def __init__(self, title: str, body: str) -> None:
        super().__init__(body)
        self.title = title


class DemoScreen(Screen):
    """Screen custom: Tab/Shift+Tab cambiano tab invece di spostare il focus.

    Nota: la Screen di default di Textual usa Tab per la navigazione del
    focus e "consuma" l'evento prima che arrivi alle binding dell'App.
    Qui le binding sono sulla Screen, quindi hanno la precedenza.
    """

    BINDINGS = [
        Binding("tab", "app.next_tab", "Tab succ."),
        Binding("shift+tab", "app.prev_tab", "Tab prec."),
    ]


class DemoApp(App):
    """App demo: tab + pannello + status bar degli eventi."""

    def get_default_screen(self) -> Screen:
        # In Textual 8.x la screen di default si imposta qui
        # (il dict SCREENS non viene più usato per la screen iniziale).
        return DemoScreen(id="_default")

    CSS = """
    Screen {
        layout: vertical;
    }
    #content {
        height: 1fr;
        padding: 1 2;
    }
    #status {
        height: 1;
        background: $boost;
        color: $text;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("f1", "goto_tab(0)", "Tab 1"),
        Binding("f2", "goto_tab(1)", "Tab 2"),
        Binding("f3", "goto_tab(2)", "Tab 3"),
        Binding("ctrl+q", "quit", "Esci"),
    ]

    TABS = ["Home", "Codice", "Impostazioni"]
    current_tab = reactive(0)

    def compose(self) -> ComposeResult:
        yield TabBar(self.TABS)
        with Vertical(id="content"):
            yield TabPanel(
                "Home",
                "Benvenuto nella demo TUI.\n\n"
                "• Clicca sulle tab in alto (mouse)\n"
                "• Tab / Shift+Tab per cambiare tab\n"
                "• F1, F2, F3 per saltare a una tab\n"
                "• Ctrl+Q per uscire\n\n"
                "Lo status bar in basso mostra l'ultimo evento\n"
                "ricevuto: così vedi come il terminale invia\n"
                "click e tasti all'applicazione.",
            )
            yield TabPanel(
                "Codice",
                "Questa tab simula un pannello 'codice'.\n\n"
                "In una TUI reale (Copilot CLI, Claude Code) ogni tab\n"
                "contiene un widget: output dello stream LLM,\n"
                "diff, lista file, ecc. Il framework gestisce\n"
                "il rendering a celle e il diff del frame.",
            )
            yield TabPanel(
                "Impostazioni",
                "Questa tab simula un pannello 'impostazioni'.\n\n"
                "Sotto il cofano: il terminale invia gli eventi\n"
                "mouse come sequenze escape (modalità SGR\n"
                "\\x1b[<0;col;rowM) e i tasti come byte grezzi\n"
                "in raw mode. Il framework li parsea e li\n"
                "converte in eventi Python (Click, Key).",
            )
        yield Static("", id="status")
        # Footer in basso: mostra i comandi (keybinding) disponibili.
        # Le tab vere restano in alto; qui ci sono solo i controlli.
        yield Footer()

    def on_mount(self) -> None:
        self.set_status("App avviata — clicca una tab o premi Tab")

    def set_status(self, text: str) -> None:
        self.query_one("#status", Static).update(text)

    # --- gestione tab -------------------------------------------------

    def on_tab_bar_tab_selected(self, event: TabBar.TabSelected) -> None:
        self.show_tab(event.index)

    def show_tab(self, index: int) -> None:
        self.current_tab = index
        panels = self.query(TabPanel)
        for i, panel in enumerate(panels):
            panel.display = i == index
        # Aggiorna anche l'evidenziazione della tab bar: così il
        # highlight segue la tab attiva sia da click che da tastiera.
        self.query_one(TabBar).set_active(index)
        self.set_status(f"Tab attiva: {self.TABS[index]}")

    def action_next_tab(self) -> None:
        self.show_tab((self.current_tab + 1) % len(self.TABS))

    def action_prev_tab(self) -> None:
        self.show_tab((self.current_tab - 1) % len(self.TABS))

    def action_goto_tab(self, index: int) -> None:
        self.show_tab(index)

    # --- visualizzazione eventi (per capire il meccanismo) -----------

    def on_click(self, event: Click) -> None:
        # Click fuori dalla tab bar: li mostriamo per vedere
        # le coordinate che il terminale ha inviato.
        # (l'evento bolle fino all'App anche dai click sulle tab)
        if event.widget is not None and not str(event.widget.id).startswith("tab-"):
            self.set_status(
                f"Click in ({event.x}, {event.y}) "
                f"sul widget '{event.widget.id or type(event.widget).__name__}'"
            )

    def on_key(self, event: Key) -> None:
        if event.key in ("tab", "shift+tab", "f1", "f2", "f3", "ctrl+q"):
            return  # già gestiti dalle binding
        self.set_status(f"Key: {event.key}")


if __name__ == "__main__":
    DemoApp().run()
