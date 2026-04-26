from __future__ import annotations

from datetime import datetime
import re
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


def build_ui() -> tk.Tk:
    root = tk.Tk()
    root.title("究極二択くん ローカル管理")
    root.geometry("620x360")
    root.resizable(False, False)
    root.columnconfigure(0, weight=1)

    frame = ttk.Frame(root, padding=16)
    frame.grid(row=0, column=0, sticky="nsew")
    frame.columnconfigure(1, weight=1)

    content = read_index()
    current_version, current_updated = extract_meta(content)

    version_var = tk.StringVar(value=current_version)
    updated_var = tk.StringVar(value=current_updated)
    status_var = tk.StringVar(value="準備完了")

    ttk.Label(frame, text="アプリ情報編集（index.html）").grid(
        row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
    )
    ttk.Label(frame, text=f"対象: {INDEX_PATH}").grid(
        row=1, column=0, columnspan=2, sticky="w", pady=(0, 12)
    )

    ttk.Label(frame, text="バージョン").grid(row=2, column=0, sticky="w")
    version_entry = ttk.Entry(frame, textvariable=version_var)
    version_entry.grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=(0, 8))

    ttk.Label(frame, text="最終更新日").grid(row=3, column=0, sticky="w")
    updated_entry = ttk.Entry(frame, textvariable=updated_var)
    updated_entry.grid(row=3, column=1, sticky="ew", padx=(8, 0), pady=(0, 8))

    def set_today() -> None:
        updated_var.set(datetime.now().strftime("%Y-%m-%d"))

    ttk.Button(frame, text="本日の日付にする", command=set_today).grid(
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

    ttk.Button(frame, text="index.html を更新する", command=handle_update_meta).grid(
        row=5, column=0, columnspan=2, sticky="ew", pady=(4, 16)
    )

    ttk.Separator(frame, orient="horizontal").grid(
        row=6, column=0, columnspan=2, sticky="ew", pady=4
    )

    ttk.Label(frame, text="database.db 同期（上書き）").grid(
        row=7, column=0, columnspan=2, sticky="w", pady=(8, 8)
    )
    ttk.Label(frame, text=f"ダウンロード元: {DB_URL}").grid(
        row=8, column=0, columnspan=2, sticky="w"
    )
    ttk.Label(frame, text=f"保存先: {DB_PATH}").grid(
        row=9, column=0, columnspan=2, sticky="w", pady=(0, 8)
    )
    db_last_modified_var = tk.StringVar(value=format_db_last_modified())

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

    ttk.Button(frame, text="オンライン版で上書きする", command=handle_sync_db).grid(
        row=10, column=0, columnspan=2, sticky="ew", pady=(4, 6)
    )
    ttk.Label(frame, textvariable=db_last_modified_var).grid(
        row=11, column=0, columnspan=2, sticky="w", pady=(0, 6)
    )

    ttk.Label(frame, textvariable=status_var).grid(
        row=12, column=0, columnspan=2, sticky="w"
    )

    version_entry.focus_set()
    updated_entry.icursor(tk.END)
    return root


if __name__ == "__main__":
    app_ui = build_ui()
    app_ui.mainloop()
