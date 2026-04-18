import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from plotly.offline import plot


class QuantDashboard:
    """
    Base desktop dashboard for backtest analysis.

    This is intentionally built as a framework so you can plug in your own:
    - strategy logic
    - metrics
    - trade logs
    - equity curve
    - drawdown calculations
    - parameter summaries
    """

    BG = "#0f1117"
    PANEL = "#161b22"
    PANEL_ALT = "#1c2128"
    BORDER = "#2d333b"
    TEXT = "#e6edf3"
    MUTED = "#8b949e"
    ACCENT = "#58a6ff"
    POSITIVE = "#3fb950"
    NEGATIVE = "#f85149"
    WARNING = "#d29922"

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Quant Backtesting Dashboard")
        self.root.geometry("1450x920")
        self.root.minsize(1200, 760)
        self.root.configure(bg=self.BG)

        self.results_df: Optional[pd.DataFrame] = None
        self.trades_df: Optional[pd.DataFrame] = None
        self.metrics: dict = {}

        self._configure_styles()
        self._build_layout()
        self._load_demo_data()
        self.refresh_dashboard()

    def _configure_styles(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "Dashboard.TFrame",
            background=self.BG,
        )
        style.configure(
            "Panel.TFrame",
            background=self.PANEL,
            borderwidth=1,
            relief="solid",
        )
        style.configure(
            "PanelAlt.TFrame",
            background=self.PANEL_ALT,
            borderwidth=1,
            relief="solid",
        )
        style.configure(
            "Title.TLabel",
            background=self.BG,
            foreground=self.TEXT,
            font=("Segoe UI", 24, "bold"),
        )
        style.configure(
            "Subtitle.TLabel",
            background=self.BG,
            foreground=self.MUTED,
            font=("Segoe UI", 10),
        )
        style.configure(
            "PanelTitle.TLabel",
            background=self.PANEL,
            foreground=self.TEXT,
            font=("Segoe UI", 13, "bold"),
        )
        style.configure(
            "MetricLabel.TLabel",
            background=self.PANEL,
            foreground=self.MUTED,
            font=("Segoe UI", 10),
        )
        style.configure(
            "MetricValue.TLabel",
            background=self.PANEL,
            foreground=self.TEXT,
            font=("Segoe UI", 18, "bold"),
        )
        style.configure(
            "Control.TButton",
            background=self.ACCENT,
            foreground="white",
            font=("Segoe UI", 10, "bold"),
            borderwidth=0,
            focusthickness=0,
            padding=8,
        )
        style.map(
            "Control.TButton",
            background=[("active", "#388bfd")],
        )

        style.configure(
            "Dark.Treeview",
            background=self.PANEL_ALT,
            foreground=self.TEXT,
            fieldbackground=self.PANEL_ALT,
            rowheight=28,
            bordercolor=self.BORDER,
            borderwidth=0,
            font=("Consolas", 10),
        )
        style.configure(
            "Dark.Treeview.Heading",
            background=self.PANEL,
            foreground=self.TEXT,
            font=("Segoe UI", 10, "bold"),
            relief="flat",
        )
        style.map(
            "Dark.Treeview",
            background=[("selected", "#243b53")],
            foreground=[("selected", self.TEXT)],
        )

    def _build_layout(self) -> None:
        self.main = ttk.Frame(self.root, style="Dashboard.TFrame", padding=16)
        self.main.pack(fill="both", expand=True)

        self._build_header()
        self._build_controls()
        self._build_metric_cards()
        self._build_lower_layout()

    def _build_header(self) -> None:
        header = ttk.Frame(self.main, style="Dashboard.TFrame")
        header.pack(fill="x", pady=(0, 10))

        ttk.Label(header, text="Quant Backtesting Dashboard", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Base GUI shell for strategy analytics, results, trade logs, and charts.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(2, 0))

    def _build_controls(self) -> None:
        controls = ttk.Frame(self.main, style="Dashboard.TFrame")
        controls.pack(fill="x", pady=(0, 14))

        ttk.Button(controls, text="Load Results CSV", style="Control.TButton", command=self.load_results_csv).pack(side="left", padx=(0, 8))
        ttk.Button(controls, text="Load Trades CSV", style="Control.TButton", command=self.load_trades_csv).pack(side="left", padx=(0, 8))
        ttk.Button(controls, text="Refresh Dashboard", style="Control.TButton", command=self.refresh_dashboard).pack(side="left", padx=(0, 8))
        ttk.Button(controls, text="Open Plotly Chart", style="Control.TButton", command=self.show_interactive_chart).pack(side="left", padx=(0, 8))

        self.status_var = tk.StringVar(value="Ready")
        status_label = tk.Label(
            controls,
            textvariable=self.status_var,
            bg=self.BG,
            fg=self.MUTED,
            font=("Segoe UI", 10),
        )
        status_label.pack(side="right")

    def _build_metric_cards(self) -> None:
        cards = ttk.Frame(self.main, style="Dashboard.TFrame")
        cards.pack(fill="x", pady=(0, 14))

        self.metric_labels = {}
        titles = [
            "Total Return",
            "Sharpe Ratio",
            "Max Drawdown",
            "Win Rate",
            "Total Trades",
            "Profit Factor",
        ]

        for i, title in enumerate(titles):
            card = ttk.Frame(cards, style="Panel.TFrame", padding=14)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0))
            cards.columnconfigure(i, weight=1)

            ttk.Label(card, text=title, style="MetricLabel.TLabel").pack(anchor="w")
            value_label = ttk.Label(card, text="--", style="MetricValue.TLabel")
            value_label.pack(anchor="w", pady=(8, 0))
            self.metric_labels[title] = value_label

    def _build_lower_layout(self) -> None:
        lower = ttk.Frame(self.main, style="Dashboard.TFrame")
        lower.pack(fill="both", expand=True)

        left = ttk.Frame(lower, style="Dashboard.TFrame")
        left.pack(side="left", fill="both", expand=True)

        right = ttk.Frame(lower, style="Dashboard.TFrame")
        right.pack(side="left", fill="both", expand=True, padx=(14, 0))

        self._build_summary_panel(left)
        self._build_trades_panel(left)
        self._build_notes_panel(right)
        self._build_parameters_panel(right)

    def _build_summary_panel(self, parent: ttk.Frame) -> None:
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=14)
        panel.pack(fill="x", pady=(0, 14))

        ttk.Label(panel, text="Run Summary", style="PanelTitle.TLabel").pack(anchor="w", pady=(0, 10))

        self.summary_text = tk.Text(
            panel,
            height=10,
            bg=self.PANEL,
            fg=self.TEXT,
            insertbackground=self.TEXT,
            relief="flat",
            font=("Consolas", 10),
            wrap="word",
        )
        self.summary_text.pack(fill="x")

    def _build_trades_panel(self, parent: ttk.Frame) -> None:
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=14)
        panel.pack(fill="both", expand=True)

        ttk.Label(panel, text="Recent Trades", style="PanelTitle.TLabel").pack(anchor="w", pady=(0, 10))

        columns = ("entry_time", "side", "entry_price", "exit_price", "pnl", "r_multiple")
        self.trades_table = ttk.Treeview(panel, columns=columns, show="headings", style="Dark.Treeview")

        headings = {
            "entry_time": "Entry Time",
            "side": "Side",
            "entry_price": "Entry",
            "exit_price": "Exit",
            "pnl": "PnL",
            "r_multiple": "R",
        }

        widths = {
            "entry_time": 150,
            "side": 70,
            "entry_price": 90,
            "exit_price": 90,
            "pnl": 90,
            "r_multiple": 70,
        }

        for col in columns:
            self.trades_table.heading(col, text=headings[col])
            self.trades_table.column(col, width=widths[col], anchor="center")

        scrollbar = ttk.Scrollbar(panel, orient="vertical", command=self.trades_table.yview)
        self.trades_table.configure(yscrollcommand=scrollbar.set)

        self.trades_table.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _build_notes_panel(self, parent: ttk.Frame) -> None:
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=14)
        panel.pack(fill="both", expand=True, pady=(0, 14))

        ttk.Label(panel, text="Strategy Notes", style="PanelTitle.TLabel").pack(anchor="w", pady=(0, 10))

        self.notes_text = tk.Text(
            panel,
            bg=self.PANEL,
            fg=self.TEXT,
            insertbackground=self.TEXT,
            relief="flat",
            font=("Consolas", 10),
            wrap="word",
        )
        self.notes_text.pack(fill="both", expand=True)
        self.notes_text.insert(
            "1.0",
            "Use this section to display:\n"
            "- strategy description\n"
            "- assumptions\n"
            "- validation notes\n"
            "- session filters\n"
            "- parameter notes\n"
            "- comments on model risk\n"
        )

    def _build_parameters_panel(self, parent: ttk.Frame) -> None:
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=14)
        panel.pack(fill="x")

        ttk.Label(panel, text="Run Parameters", style="PanelTitle.TLabel").pack(anchor="w", pady=(0, 10))

        self.params_var = tk.StringVar(value="No parameters loaded yet.")
        label = tk.Label(
            panel,
            textvariable=self.params_var,
            bg=self.PANEL,
            fg=self.TEXT,
            font=("Consolas", 10),
            justify="left",
            anchor="w",
        )
        label.pack(fill="x")

    def _load_demo_data(self) -> None:
        np.random.seed(42)
        periods = 220
        dates = pd.date_range("2025-01-01", periods=periods, freq="D")

        returns = np.random.normal(0.0008, 0.012, periods)
        equity = 100000 * (1 + returns).cumprod()
        peak = pd.Series(equity).cummax()
        drawdown = (pd.Series(equity) - peak) / peak

        self.results_df = pd.DataFrame(
            {
                "date": dates,
                "returns": returns,
                "equity": equity,
                "drawdown": drawdown,
            }
        )

        self.trades_df = pd.DataFrame(
            {
                "entry_time": pd.date_range("2025-02-01", periods=20, freq="3D"),
                "side": np.random.choice(["LONG", "SHORT"], size=20),
                "entry_price": np.round(np.random.uniform(18000, 21000, size=20), 2),
                "exit_price": np.round(np.random.uniform(18000, 21000, size=20), 2),
                "pnl": np.round(np.random.normal(120, 450, size=20), 2),
                "r_multiple": np.round(np.random.normal(0.45, 1.25, size=20), 2),
            }
        )

    def load_results_csv(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Select results CSV",
            filetypes=[("CSV Files", "*.csv")],
        )
        if not file_path:
            return

        try:
            df = pd.read_csv(file_path)
            self.results_df = df
            self.status_var.set(f"Loaded results: {Path(file_path).name}")
            self.refresh_dashboard()
        except Exception as exc:
            messagebox.showerror("Load Error", f"Could not load results CSV.\n\n{exc}")

    def load_trades_csv(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Select trades CSV",
            filetypes=[("CSV Files", "*.csv")],
        )
        if not file_path:
            return

        try:
            df = pd.read_csv(file_path)
            self.trades_df = df
            self.status_var.set(f"Loaded trades: {Path(file_path).name}")
            self.refresh_dashboard()
        except Exception as exc:
            messagebox.showerror("Load Error", f"Could not load trades CSV.\n\n{exc}")

    def refresh_dashboard(self) -> None:
        if self.results_df is None or self.results_df.empty:
            self.status_var.set("No results data loaded")
            return

        self.metrics = self._build_base_metrics(self.results_df, self.trades_df)
        self._update_metric_cards()
        self._update_summary_text()
        self._update_trades_table()
        self._update_params_panel()
        self.status_var.set("Dashboard refreshed")

    def _build_base_metrics(self, results_df: pd.DataFrame, trades_df: Optional[pd.DataFrame]) -> dict:
        df = results_df.copy()

        if "returns" not in df.columns and "equity" in df.columns:
            df["returns"] = pd.Series(df["equity"]).pct_change().fillna(0)

        if "drawdown" not in df.columns and "equity" in df.columns:
            equity = pd.Series(df["equity"])
            peak = equity.cummax()
            df["drawdown"] = (equity - peak) / peak

        total_return = 0.0
        sharpe = 0.0
        max_drawdown = 0.0

        if "equity" in df.columns and len(df) > 1:
            total_return = (df["equity"].iloc[-1] / df["equity"].iloc[0]) - 1

        if "returns" in df.columns and df["returns"].std() != 0:
            sharpe = (df["returns"].mean() / df["returns"].std()) * np.sqrt(252)

        if "drawdown" in df.columns:
            max_drawdown = df["drawdown"].min()

        total_trades = 0
        win_rate = 0.0
        profit_factor = 0.0

        if trades_df is not None and not trades_df.empty and "pnl" in trades_df.columns:
            total_trades = len(trades_df)
            wins = (trades_df["pnl"] > 0).sum()
            win_rate = wins / total_trades if total_trades else 0.0

            gross_profit = trades_df.loc[trades_df["pnl"] > 0, "pnl"].sum()
            gross_loss = abs(trades_df.loc[trades_df["pnl"] < 0, "pnl"].sum())
            profit_factor = gross_profit / gross_loss if gross_loss != 0 else np.nan

        return {
            "Total Return": f"{total_return:.2%}",
            "Sharpe Ratio": f"{sharpe:.2f}",
            "Max Drawdown": f"{max_drawdown:.2%}",
            "Win Rate": f"{win_rate:.2%}",
            "Total Trades": str(total_trades),
            "Profit Factor": f"{profit_factor:.2f}" if not np.isnan(profit_factor) else "∞",
            "raw": {
                "total_return": total_return,
                "sharpe": sharpe,
                "max_drawdown": max_drawdown,
                "win_rate": win_rate,
                "total_trades": total_trades,
                "profit_factor": profit_factor,
            },
        }

    def _update_metric_cards(self) -> None:
        for key, label in self.metric_labels.items():
            label.config(text=self.metrics.get(key, "--"))

            value = self.metrics.get(key, "")
            color = self.TEXT
            if key in {"Total Return", "Sharpe Ratio", "Win Rate", "Profit Factor"}:
                if isinstance(value, str) and value not in {"--", "∞"}:
                    if "-" in value:
                        color = self.NEGATIVE
                    else:
                        color = self.POSITIVE
            if key == "Max Drawdown":
                color = self.WARNING
            label.config(foreground=color)

    def _update_summary_text(self) -> None:
        self.summary_text.delete("1.0", tk.END)

        df = self.results_df.copy()
        start_date = str(df["date"].iloc[0])[:10] if "date" in df.columns else "N/A"
        end_date = str(df["date"].iloc[-1])[:10] if "date" in df.columns else "N/A"

        summary = (
            f"Backtest period: {start_date} to {end_date}\n"
            f"Observations: {len(df)}\n"
            f"\n"
            f"Core metrics:\n"
            f"- Total Return: {self.metrics.get('Total Return', '--')}\n"
            f"- Sharpe Ratio: {self.metrics.get('Sharpe Ratio', '--')}\n"
            f"- Max Drawdown: {self.metrics.get('Max Drawdown', '--')}\n"
            f"- Win Rate: {self.metrics.get('Win Rate', '--')}\n"
            f"- Total Trades: {self.metrics.get('Total Trades', '--')}\n"
            f"- Profit Factor: {self.metrics.get('Profit Factor', '--')}\n"
            f"\n"
            f"Replace this block later with your own strategy-specific summary,\n"
            f"risk commentary, validation results, walk-forward notes, and session analysis.\n"
        )
        self.summary_text.insert("1.0", summary)

    def _update_trades_table(self) -> None:
        for row in self.trades_table.get_children():
            self.trades_table.delete(row)

        if self.trades_df is None or self.trades_df.empty:
            return

        display_df = self.trades_df.copy().tail(20)
        required_columns = ["entry_time", "side", "entry_price", "exit_price", "pnl", "r_multiple"]

        for col in required_columns:
            if col not in display_df.columns:
                display_df[col] = np.nan

        for _, row in display_df.iterrows():
            values = [
                str(row["entry_time"])[:19],
                row["side"],
                self._fmt_num(row["entry_price"]),
                self._fmt_num(row["exit_price"]),
                self._fmt_num(row["pnl"]),
                self._fmt_num(row["r_multiple"]),
            ]
            self.trades_table.insert("", tk.END, values=values)

    def _update_params_panel(self) -> None:
        self.params_var.set(
            "symbol = NQ\n"
            "timeframe = 1m\n"
            "starting_capital = 100000\n"
            "commission = user_defined\n"
            "slippage = user_defined\n"
            "risk_per_trade = user_defined\n"
            "strategy_name = your_strategy_here"
        )

    def show_interactive_chart(self) -> None:
        if self.results_df is None or self.results_df.empty:
            messagebox.showwarning("No Data", "No results data available for charting.")
            return

        df = self.results_df.copy()
        if "date" not in df.columns:
            df["date"] = np.arange(len(df))

        if "drawdown" not in df.columns and "equity" in df.columns:
            equity = pd.Series(df["equity"])
            peak = equity.cummax()
            df["drawdown"] = (equity - peak) / peak

        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            subplot_titles=("Equity Curve", "Drawdown"),
            row_heights=[0.7, 0.3],
        )

        if "equity" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["date"],
                    y=df["equity"],
                    mode="lines",
                    name="Equity",
                    line=dict(color="#58a6ff", width=2),
                ),
                row=1,
                col=1,
            )

        if "drawdown" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["date"],
                    y=df["drawdown"],
                    mode="lines",
                    name="Drawdown",
                    fill="tozeroy",
                    line=dict(color="#f85149", width=1.5),
                ),
                row=2,
                col=1,
            )

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor=self.BG,
            plot_bgcolor=self.PANEL,
            font=dict(color=self.TEXT),
            title="Backtest Performance",
            height=800,
            margin=dict(l=40, r=40, t=60, b=40),
        )

        plot(fig, auto_open=True)

    @staticmethod
    def _fmt_num(value) -> str:
        if pd.isna(value):
            return "--"
        try:
            return f"{float(value):.2f}"
        except Exception:
            return str(value)


if __name__ == "__main__":
    root = tk.Tk()
    app = QuantDashboard(root)
    root.mainloop()
