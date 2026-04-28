from __future__ import annotations

from datetime import datetime
import re
import sqlite3
import webbrowser
from pathlib import Path
from urllib.request import urlopen

import tkinter as tk
from tkinter import messagebox, ttk


BASE_DIR = Path(__file__).resolve().parent
INDEX_PATH = BASE_DIR / "templates" / "index.html"
DB_PATH = BASE_DIR / "instance" / "database.db"
DB_URL = "https://sigepiyo338.pythonanywhere.com/static/database.db"

VERSION_PATTERN = re.compile(r'(<span id="app-version">)([^<]*)(</span>)')
UPDATED_PATTERN = re.compile(
    r"<span(?:\s+id=\"last-updated\")?>\s*最終更新:\s*[^<]*</span>"
)

def read_index() -> str:
    return INDEX_PATH.read_text(encoding="utf-8")


def write_index(content: str) -> None:
    INDEX_PATH.write_text(content, encoding="utf-8")


def extract_meta(content: str) -> tuple[str, str]:
    version_match = VERSION_PATTERN.search(content)
    version = version_match.group(2).strip() if version_match else ""

    updated_match = re.search(r"最終更新:\s*([^<\n]+)", content)
    updated = updated_match.group(1).strip() if updated_match else ""

    return version, updated


def replace_meta(content: str, version: str, updated: str) -> str:
    new_content, version_replaced = VERSION_PATTERN.subn(
        rf"\1{version}\3", content, count=1
    )
    if version_replaced == 0:
        raise ValueError("app-version の `<span id=\"app-version\">` が見つかりません。")

    replacement = f"<span>最終更新: {updated}</span>"
    new_content, updated_replaced = UPDATED_PATTERN.subn(
        replacement, new_content, count=1
    )
    if updated_replaced == 0:
        raise ValueError("最終更新表示の `<span>` が見つかりません。")

    return new_content


def update_meta(version: str, updated: str) -> None:
    if not version or not updated:
        raise ValueError("バージョンと最終更新日は必須です。")

    content = read_index()
    updated_content = replace_meta(content, version=version, updated=updated)
    write_index(updated_content)


def sync_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(DB_URL, timeout=20) as response:
        data = response.read()
    if not data:
        raise ValueError("ダウンロードしたDBが空です。")
    DB_PATH.write_bytes(data)


def format_db_last_modified() -> str:
    if not DB_PATH.exists():
        return "ローカルDB最終更新日: （database.db が存在しません）"
    modified_at = datetime.fromtimestamp(DB_PATH.stat().st_mtime)
    return f"ローカルDB最終更新日: {modified_at.strftime('%Y-%m-%d %H:%M:%S')}"


def read_personalities() -> tuple[list[str], list[tuple]]:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"database.db が見つかりません: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        columns_cursor = conn.execute("PRAGMA table_info(personalities)")
        columns = [row[1] for row in columns_cursor.fetchall()]
        if not columns:
            raise ValueError("personalities テーブルが見つかりません。")

        rows_cursor = conn.execute("SELECT * FROM personalities ORDER BY id")
        rows = rows_cursor.fetchall()
    return columns, rows


def delete_personality_and_related_scores(personality_id: int) -> tuple[int, int]:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"database.db が見つかりません: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM scores WHERE personality_id = ?", (personality_id,))
        deleted_scores = cursor.rowcount if cursor.rowcount != -1 else 0
        cursor.execute("DELETE FROM personalities WHERE id = ?", (personality_id,))
        deleted_personalities = cursor.rowcount if cursor.rowcount != -1 else 0
        conn.commit()

    if deleted_personalities == 0:
        raise ValueError("選択された personality は既に存在しない可能性があります。")
    return deleted_personalities, deleted_scores


def build_ui() -> tk.Tk:
    root = tk.Tk()
    root.title("究極二択くん ローカル管理ツール")
    root.geometry("620x360")
    root.resizable(True, True)
    root.minsize(620, 360)
    root.columnconfigure(0, weight=1)

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure(
        "Manager.TNotebook",
        background="#d6d6d6",
        borderwidth=1,
        relief="solid",
    )
    style.configure(
        "Manager.TNotebook.Tab",
        background="#c8c8c8",
        foreground="#1f1f1f",
        borderwidth=1,
        padding=(12, 5),
    )
    style.map(
        "Manager.TNotebook.Tab",
        background=[("selected", "#ffffff"), ("active", "#e3e3e3")],
        foreground=[("selected", "#000000"), ("active", "#1a1a1a")],
        padding=[("selected", (16, 8)), ("!selected", (12, 5))],
        relief=[("selected", "raised"), ("!selected", "ridge")],
    )
    style.configure("Manager.TFrame", background="#f6f6f6")

    frame = ttk.Frame(root, padding=16)
    frame.grid(row=0, column=0, sticky="nsew")
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(0, weight=1)

    content = read_index()
    current_version, current_updated = extract_meta(content)

    version_var = tk.StringVar(value=current_version)
    updated_var = tk.StringVar(value=current_updated)
    status_var = tk.StringVar(value="準備完了")
    db_last_modified_var = tk.StringVar(value=format_db_last_modified())

    notebook = ttk.Notebook(frame, style="Manager.TNotebook")
    notebook.grid(row=0, column=0, sticky="nsew")

    version_tab = ttk.Frame(notebook, style="Manager.TFrame", padding=12)
    version_tab.columnconfigure(1, weight=1)
    notebook.add(version_tab, text="バージョン管理")

    ttk.Label(version_tab, text="アプリ情報収集（index.html）").grid(
        row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
    )
    ttk.Label(version_tab, text=f"対象: {INDEX_PATH}").grid(
        row=1, column=0, columnspan=2, sticky="w", pady=(0, 12)
    )
    ttk.Label(version_tab, text="バージョン").grid(row=2, column=0, sticky="w")
    version_entry = ttk.Entry(version_tab, textvariable=version_var)
    version_entry.grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=(0, 8))

    ttk.Label(version_tab, text="最終更新日").grid(row=3, column=0, sticky="w")
    updated_entry = ttk.Entry(version_tab, textvariable=updated_var)
    updated_entry.grid(row=3, column=1, sticky="ew", padx=(8, 0), pady=(0, 8))

    def set_today() -> None:
        updated_var.set(datetime.now().strftime("%Y-%m-%d"))

    ttk.Button(version_tab, text="本日の日付にする", command=set_today).grid(
        row=4, column=1, sticky="w", padx=(8, 0), pady=(0, 8)
    )

    def handle_update_meta() -> None:
        try:
            update_meta(version_var.get().strip(), updated_var.get().strip())
            status_var.set("index.html を更新しました。")
            messagebox.showinfo("成功", "index.html を更新しました。")
        except Exception as exc:
            status_var.set(f"更新失敗: {exc}")
            messagebox.showerror("エラー", f"更新失敗: {exc}")

    ttk.Button(version_tab, text="index.html を更新する", command=handle_update_meta).grid(
        row=5, column=0, columnspan=2, sticky="ew", pady=(4, 16)
    )

    db_tab = ttk.Frame(notebook, style="Manager.TFrame", padding=12)
    notebook.add(db_tab, text="DB同期")

    ttk.Label(db_tab, text="database.db 同期（上書き）").grid(
        row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
    )
    ttk.Label(db_tab, text=f"ダウンロード元: {DB_URL}").grid(
        row=1, column=0, columnspan=2, sticky="w"
    )
    ttk.Label(db_tab, text=f"保存先: {DB_PATH}").grid(
        row=2, column=0, columnspan=2, sticky="w", pady=(0, 8)
    )

    def handle_sync_db() -> None:
        if not messagebox.askyesno(
            "確認", "オンライン版の database.db でローカルを上書きします。続行しますか？"
        ):
            return
        try:
            sync_db()
            db_last_modified_var.set(format_db_last_modified())
            status_var.set("database.db を上書き同期しました。")
            messagebox.showinfo("成功", "database.db を上書き同期しました。")
        except Exception as exc:
            status_var.set(f"DB同期失敗: {exc}")
            messagebox.showerror("エラー", f"DB同期失敗: {exc}")

    ttk.Button(db_tab, text="オンライン版で上書きする", command=handle_sync_db).grid(
        row=3, column=0, columnspan=2, sticky="ew", pady=(4, 6)
    )
    ttk.Label(db_tab, textvariable=db_last_modified_var).grid(
        row=4, column=0, columnspan=2, sticky="w", pady=(0, 6)
    )

    personalities_tab = ttk.Frame(notebook, style="Manager.TFrame", padding=12)
    personalities_tab.columnconfigure(0, weight=1)
    personalities_tab.rowconfigure(2, weight=1)
    notebook.add(personalities_tab, text="性格")

    ttk.Label(personalities_tab, text="性格一覧（database.db）").grid(
        row=0, column=0, sticky="w", pady=(0, 8)
    )

    personalities_container = ttk.Frame(personalities_tab)
    personalities_container.grid(row=2, column=0, sticky="nsew")
    personalities_container.columnconfigure(0, weight=1)
    personalities_container.rowconfigure(0, weight=1)

    personalities_tree = ttk.Treeview(
        personalities_container,
        show="headings",
        height=9,
    )
    personalities_tree.grid(row=0, column=0, sticky="nsew")

    personalities_scroll_y = ttk.Scrollbar(
        personalities_container,
        orient="vertical",
        command=personalities_tree.yview,
    )
    personalities_scroll_y.grid(row=0, column=1, sticky="ns")
    personalities_tree.configure(yscrollcommand=personalities_scroll_y.set)

    personalities_status_var = tk.StringVar(value="未読込")
    ttk.Label(personalities_tab, textvariable=personalities_status_var).grid(
        row=3, column=0, sticky="w", pady=(8, 0)
    )

    def reload_personalities() -> None:
        try:
            columns, rows = read_personalities()

            personalities_tree.delete(*personalities_tree.get_children())
            personalities_tree.configure(columns=columns)
            for column in columns:
                personalities_tree.heading(column, text=column)
                personalities_tree.column(column, width=110, anchor="w")

            for row in rows:
                personalities_tree.insert("", "end", values=row)

            personalities_status_var.set(f"{len(rows)} 件表示")
        except Exception as exc:
            personalities_status_var.set(f"読込失敗: {exc}")
            status_var.set(f"性格タブ読込失敗: {exc}")

    def handle_delete_selected_personality() -> None:
        selected_items = personalities_tree.selection()
        if not selected_items:
            messagebox.showwarning("未選択", "削除する行を選択してください。")
            return

        item_id = selected_items[0]
        values = personalities_tree.item(item_id, "values")
        if not values:
            messagebox.showerror("エラー", "選択行の値を取得できませんでした。")
            return

        try:
            personality_id = int(values[0])
        except (TypeError, ValueError):
            messagebox.showerror("エラー", "選択行のIDが不正です。")
            return

        if not messagebox.askyesno(
            "確認",
            f"personality_id={personality_id} を削除します。\n"
            "関連する scores も削除されます。続行しますか？",
        ):
            return

        try:
            deleted_personalities, deleted_scores = delete_personality_and_related_scores(
                personality_id
            )
            reload_personalities()
            status_var.set(
                f"性格ID {personality_id} を削除（personalities:{deleted_personalities}, scores:{deleted_scores}）"
            )
            messagebox.showinfo(
                "削除完了",
                f"personalities: {deleted_personalities} 件\nscores: {deleted_scores} 件 を削除しました。",
            )
        except Exception as exc:
            status_var.set(f"性格削除失敗: {exc}")
            messagebox.showerror("エラー", f"性格削除失敗: {exc}")

    ttk.Button(
        personalities_tab, text="一覧を再読込", command=reload_personalities
    ).grid(row=1, column=0, sticky="w")
    ttk.Button(
        personalities_tab,
        text="選択中の性格を削除（scoresも削除）",
        command=handle_delete_selected_personality,
    ).grid(row=1, column=0, sticky="e")
    reload_personalities()

    tools_tab = ttk.Frame(notebook, style="Manager.TFrame", padding=12)
    tools_tab.columnconfigure(0, weight=1)
    notebook.add(tools_tab, text="外部ツール")

    ttk.Label(tools_tab, text="・究極二択くん(オンライン版)").grid(
        row=0, column=0, sticky="w"
    )
    online_url = ttk.Label(
        tools_tab,
        text="　-　https://sigepiyo338.pythonanywhere.com/",
        foreground="#0066cc",
        cursor="hand2",
    )
    online_url.grid(row=1, column=0, sticky="w", pady=(0, 8))
    online_url.bind(
        "<Button-1>",
        lambda _event: webbrowser.open("https://sigepiyo338.pythonanywhere.com/"),
    )

    ttk.Label(tools_tab, text="・PythonAnywhere Dashboard").grid(
        row=2, column=0, sticky="w"
    )
    pa_url = ttk.Label(
        tools_tab,
        text="　-　https://www.pythonanywhere.com/",
        foreground="#0066cc",
        cursor="hand2",
    )
    pa_url.grid(row=3, column=0, sticky="w", pady=(0, 8))
    pa_url.bind(
        "<Button-1>",
        lambda _event: webbrowser.open("https://www.pythonanywhere.com/"),
    )

    ttk.Label(tools_tab, text="・Github - 2takukun_web").grid(
        row=4, column=0, sticky="w"
    )
    github_url = ttk.Label(
        tools_tab,
        text="　-　https://github.com/sigepiyo338-droid/2takukun_web",
        foreground="#0066cc",
        cursor="hand2",
    )
    github_url.grid(row=5, column=0, sticky="w")
    github_url.bind(
        "<Button-1>",
        lambda _event: webbrowser.open(
            "https://github.com/sigepiyo338-droid/2takukun_web"
        ),
    )

    ttk.Label(frame, textvariable=status_var).grid(
        row=1, column=0, sticky="w", pady=(10, 0)
    )

    version_entry.focus_set()
    updated_entry.icursor(tk.END)
    return root


if __name__ == "__main__":
    app_ui = build_ui()
    app_ui.mainloop()
