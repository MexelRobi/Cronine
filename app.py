import json
from datetime import datetime
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Input, Button, RichLog, Label, TabbedContent, TabPane, DataTable
from rich.text import Text
import cronine_core

class CronineApp(App):
    
    ENABLE_COMMAND_PALETTE = False
    
    CSS = """
    Screen {
        background: #0a0a0a;
    }
    Header {
        background: #111111;
        color: #00ff66;
        text-style: bold;
    }
    Footer {
        background: #111111;
    }
    TabbedContent {
        background: #0d0d0d;
        height: 1fr;
    }
    TabPane {
        padding: 1;
        background: #0d0d0d;
        height: 1fr;
    }
    .auth-container {
        align: center middle;
        height: 100%;
        background: #0a0a0a;
    }
    .auth-box {
        width: 50;
        height: auto;
        border: solid #00ff66;
        padding: 2;
        background: #111111;
    }
    .pane {
        width: 100%;
        height: 1fr;
        border: solid #222222;
        padding: 1;
        background: #111111;
    }
    .title {
        text-align: center;
        background: #161616;
        color: #00ff66;
        text-style: bold;
        margin-bottom: 1;
        padding: 1;
        border: solid #00ff66;
        width: 100%;
    }
    Label {
        color: #888888;
        margin-bottom: 1;
    }
    Button {
        margin-top: 1;
        margin-bottom: 1;
        width: 100%;
        background: #141414;
        color: #00ff66;
        border: solid #00ff66;
    }
    Button:hover {
        background: #00ff66;
        color: #0a0a0a;
        text-style: bold;
    }
    .btn-danger {
        background: #220000;
        color: #ff4444;
        border: solid #ff4444;
    }
    .btn-danger:hover {
        background: #ff4444;
        color: #ffffff;
    }
    Input {
        border: solid #333333;
        background: #141416;
        color: #ffffff;
        width: 100%;
        margin-bottom: 1;
    }
    Input:focus {
        border: solid #00ff66;
    }
    RichLog {
        background: #141416;
        border: solid #222222;
        margin-top: 1;
        height: 1fr;
    }
    .table-container {
        height: 1fr;
        min-height: 12;
        border: solid #222222;
        background: #141416;
        margin-bottom: 1;
    }
    DataTable {
        height: 100%;
        width: 100%;
        background: #141416;
    }
    .db-management-panel {
        height: auto;
        border: dashed #333333;
        padding: 1;
    }
    .action-row {
        height: auto;
        width: 100%;
    }
    .action-row Button {
        width: 1fr;
        margin-left: 1;
        margin-right: 1;
    }
    #auth_error_label {
        color: #ff3333;
        margin-top: 1;
        margin-bottom: 1;
        text-style: bold;
    }
    .hidden {
        display: none !important;
    }
    #auth_screen {
        height: 1fr;
    }
    #main_screen {
        height: 1fr;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def __init__(self):
        super().__init__()
        self.is_encrypted = cronine_core.is_db_encrypted()
        self.authenticated = not self.is_encrypted
        self.selected_row_data = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Container(id="auth_screen"):
            with Container(classes="auth-container"):
                with Vertical(classes="auth-box"):
                    yield Label("CRONINE ENCRYPTION SECURITY MATRIX")
                    yield Label("Enter decryption passphrase:")
                    yield Input(placeholder="Passphrase...", password=True, id="password_input")
                    yield Label("", id="auth_error_label")
                    yield Button("Unlock Core Database", id="unlock_btn")
                    
        with Container(id="main_screen"):
            with TabbedContent(id="tabs"):
                with TabPane("Record Memories", id="tab_record"):
                    with Vertical(classes="pane"):
                        yield Label("RECORD TODAY'S EXPERIENCE", classes="title")
                        yield Label("Target Date:")
                        yield Input(placeholder="YYYY-MM-DD", id="date_input")
                        yield Label("What did you experience today?")
                        yield Input(placeholder="Type your story here...", id="entry_input")
                        yield Button("Save to Encrypted Database", id="save_btn")
                        yield RichLog(id="status_log", max_lines=20)
                        
                with TabPane("AI Investigation", id="tab_ai"):
                    with Vertical(classes="pane"):
                        yield Label("SEARCH PAST MEMORIES", classes="title")
                        yield Label("Ask Cronine about the past")
                        yield Input(placeholder="Ask anything...", id="query_input")
                        yield Button("Ask Cronine Core", id="ask_btn")
                        yield RichLog(id="ai_log", max_lines=200)
                        
                with TabPane("Database Browser", id="tab_db"):
                    with Vertical(classes="pane"):
                        yield Label("LOCAL ENCRYPTED REGISTRY ARCHITECTURE", classes="title")
                        with Vertical(classes="table-container"):
                            yield DataTable(id="db_table")
                        with Vertical(classes="db-management-panel"):
                            yield Label("Selected Entry Management Layer")
                            yield Input(placeholder="Select a row above from the grid...", id="db_edit_input")
                            with Horizontal(classes="action-row"):
                                yield Button("Update Selection", id="db_update_btn")
                                yield Button("Delete Selection", id="db_delete_btn", classes="btn-danger")
                        
                with TabPane("System Settings", id="tab_settings"):
                    with Vertical(classes="pane"):
                        yield Label("CRONINE CORE SYSTEM SETTINGS", classes="title")
                        yield Label("Setup or Update Database Encryption Passphrase")
                        yield Input(placeholder="New Password...", password=True, id="new_password_input")
                        yield Button("Apply Encryption Settings", id="set_crypto_btn")
                        yield Button("Remove Encryption", id="remove_crypto_btn")
                        yield RichLog(id="settings_log", max_lines=20)
                        
        yield Footer()
    def on_mount(self) -> None:
        table = self.query_one("#db_table", DataTable)
        table.add_columns("Date Timestamp", "Entry Index", "Logged Memory Infrastructure")
        table.cursor_type = "row"
        
        if self.is_encrypted:
            self.query_one("#main_screen", Container).add_class("hidden")
            self.query_one("#auth_screen", Container).remove_class("hidden")
        else:
            self.query_one("#auth_screen", Container).add_class("hidden")
            self.query_one("#main_screen", Container).remove_class("hidden")
            self.initialize_post_auth()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "unlock_btn":
            self.action_unlock()
        elif event.button.id == "save_btn":
            self.action_save_entry()
        elif event.button.id == "ask_btn":
            self.action_ask_ai()
        elif event.button.id == "set_crypto_btn":
            self.action_setup_encryption()
        elif event.button.id == "remove_crypto_btn":
            self.action_remove_encryption()
        elif event.button.id == "db_update_btn":
            self.action_db_update()
        elif event.button.id == "db_delete_btn":
            self.action_db_delete()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "password_input":
            self.action_unlock()
        elif event.input.id == "entry_input":
            self.action_save_entry()
        elif event.input.id == "query_input":
            self.action_ask_ai()
        elif event.input.id == "new_password_input":
            self.action_setup_encryption()

    def action_unlock(self) -> None:
        inp = self.query_one("#password_input", Input)
        err_label = self.query_one("#auth_error_label", Label)
        if inp.value:
            if not cronine_core.verify_password_input(inp.value):
                err_label.update("Passphrase Verification Failed")
                inp.value = ""
                return
            cronine_core.set_encryption_password(inp.value)
            self.authenticated = True
            self.query_one("#auth_screen", Container).add_class("hidden")
            self.query_one("#main_screen", Container).remove_class("hidden")
            self.initialize_post_auth()

    def initialize_post_auth(self) -> None:
        try:
            status_log = self.query_one("#status_log", RichLog)
            status_log.clear()
            status_log.write(Text.from_markup("[bold green][+] Cryptographic Engine Active.[/bold green]"))
            status_log.write(Text.from_markup("[gray]Database unsealed successfully.[/gray]"))
            
            date_inp = self.query_one("#date_input", Input)
            date_inp.value = datetime.now().strftime("%Y-%m-%d")
            
            self.refresh_database_table()
        except Exception:
            pass

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        if not self.authenticated:
            return
        try:
            if event.pane.id == "tab_db":
                self.refresh_database_table()
            elif event.pane.id == "tab_ai":
                ai_log = self.query_one("#ai_log", RichLog)
                ai_log.clear()
                ai_log.write(Text.from_markup("[bold cyan][*] AI Core Engine Standby.[/bold cyan]"))
        except Exception:
            pass

    def refresh_database_table(self) -> None:
        if not self.authenticated:
            return
        try:
            table = self.query_one("#db_table", DataTable)
            table.clear(columns=False)
            
            db = cronine_core.load_db()
            if not db or "error" in db:
                return
                
            for date_str, entries in db.items():
                if isinstance(entries, list):
                    for idx, entry in enumerate(entries):
                        row_key = f"{date_str}::{idx}"
                        table.add_row(str(date_str), str(idx), str(entry), key=row_key)
                else:
                    row_key = f"{date_str}::0"
                    table.add_row(str(date_str), "0", str(entries), key=row_key)
        except Exception:
            pass

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        try:
            row_key_str = event.row_key.value
            if "::" in row_key_str:
                date_part, idx_part = row_key_str.split("::", 1)
                
                table = self.query_one("#db_table", DataTable)
                row_cells = table.get_row(event.row_key)
                
                self.selected_row_data = {
                    "date": date_part,
                    "index": int(idx_part),
                    "text": str(row_cells)
                }
                edit_input = self.query_one("#db_edit_input", Input)
                edit_input.value = self.selected_row_data["text"]
        except Exception:
            pass

    def action_db_update(self) -> None:
        edit_input = self.query_one("#db_edit_input", Input)
        if self.selected_row_data and edit_input.value.strip():
            cronine_core.update_entry_by_index(
                self.selected_row_data["date"],
                self.selected_row_data["index"],
                edit_input.value.strip()
            )
            edit_input.value = ""
            self.selected_row_data = None
            self.refresh_database_table()

    def action_db_delete(self) -> None:
        edit_input = self.query_one("#db_edit_input", Input)
        if self.selected_row_data:
            cronine_core.delete_entry_by_index(
                self.selected_row_data["date"],
                self.selected_row_data["index"]
            )
            edit_input.value = ""
            self.selected_row_data = None
            self.refresh_database_table()

    def action_save_entry(self) -> None:
        date_inp = self.query_one("#date_input", Input)
        inp = self.query_one("#entry_input", Input)
        status_log = self.query_one("#status_log", RichLog)
        
        target_date = date_inp.value.strip()
        if not target_date:
            target_date = datetime.now().strftime("%Y-%m-%d")
            
        if inp.value.strip():
            res = cronine_core.save_entry(inp.value.strip(), date_str=target_date)
            if res == "error_locked":
                status_log.write(Text.from_markup("[bold red][!] Key validation layer fault.[/bold red]"))
            else:
                status_log.write(Text.from_markup(f"[green][+][/green] Committed to layer for [yellow]{res}[/yellow]"))
                inp.value = ""
                self.refresh_database_table()
        else:
            status_log.write(Text.from_markup("[red][!][/red] Input verification failure."))

    def action_ask_ai(self) -> None:
        inp = self.query_one("#query_input", Input)
        if inp.value.strip():
            query_text = inp.value.strip()
            inp.value = ""
            self.run_worker(lambda: self.run_background_inference(query_text), thread=True)

    def run_background_inference(self, query_text: str) -> None:
        try:
            ai_log = self.query_one("#ai_log", RichLog)
            self.call_from_thread(ai_log.write, Text.from_markup(f"\n[bold yellow]User >[/bold yellow] {query_text}"))
            self.call_from_thread(ai_log.write, Text.from_markup("[bold blue][*] Running secure local model contextual decryption...[/bold blue]"))
            
            response = cronine_core.ask_cronine(query_text)
            
            self.call_from_thread(ai_log.write, Text.from_markup(f"[bold green]Cronine >[/bold green] {response}"))
        except Exception:
            pass

    def action_setup_encryption(self) -> None:
        inp = self.query_one("#new_password_input", Input)
        log = self.query_one("#settings_log", RichLog)
        if inp.value.strip():
            current_db = cronine_core.load_db()
            if "error" in current_db:
                log.write(Text.from_markup("[bold red][!] Cannot re-encrypt a locked database.[/bold red]"))
                return
            cronine_core.store_password_hash(inp.value.strip())
            cronine_core.set_encryption_password(inp.value.strip())
            cronine_core.save_db(current_db)
            log.write(Text.from_markup("[bold green][+] AES-256 layer successfully activated and password hash recorded.[/bold green]"))
            inp.value = ""
        else:
            log.write(Text.from_markup("[bold red][!] Cryptographic passphrase cannot be empty.[/bold red]"))

    def action_remove_encryption(self) -> None:
        log = self.query_one("#settings_log", RichLog)
        current_db = cronine_core.load_db()
        if "error" in current_db:
            log.write(Text.from_markup("[bold red][!] Cannot decrypt database without unlocking first.[/bold red]"))
            return
        cronine_core.clear_password_hash()
        cronine_core.clear_encryption_key()
        cronine_core.save_db(current_db)
        log.write(Text.from_markup("[bold yellow][-] Encryption removed. Database saved as plaintext json.[/bold yellow]"))

if __name__ == "__main__":
    app = CronineApp()
    app.run()
