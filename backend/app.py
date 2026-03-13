from __future__ import annotations

import io
import os
import re
import sqlite3
from typing import Dict, List, Optional

import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MASTER_CSV = os.path.join(BASE_DIR, "DEVOLUCIONES_TOTALES_FEBRERO_2026_3.csv")
DB_PATH = os.path.join(BASE_DIR, "data.db")

app = Flask(__name__)
CORS(app)


def parse_csv_text(text: str) -> pd.DataFrame:
    lines = text.splitlines()
    header_index = next(
        (idx for idx, line in enumerate(lines) if line.strip().startswith("FECHA,")),
        None,
    )
    if header_index is None:
        return pd.DataFrame()

    payload = "\n".join(lines[header_index:])
    return pd.read_csv(io.StringIO(payload))


def read_csv_with_header(source) -> pd.DataFrame:
    if isinstance(source, str):
        if not os.path.exists(source):
            return pd.DataFrame()
        with open(source, "r", encoding="utf-8") as handle:
            text = handle.read()
    else:
        raw = source.read()
        if isinstance(raw, bytes):
            text = raw.decode("utf-8", errors="ignore")
        else:
            text = str(raw)

    return parse_csv_text(text)


def get_db() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with get_db() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month TEXT NOT NULL,
                csv_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_uploads_month ON uploads (month)"
        )


def derive_month_from_filename(filename: str) -> str:
    stem = os.path.splitext(os.path.basename(filename))[0]
    token = stem.replace("DEVOLUCIONES_TOTALES_", "")
    token = re.sub(r"_\d+$", "", token)
    token = token.replace("_", " ")
    return token.title() if token else "Mes Actual"


def seed_db_if_empty() -> None:
    with get_db() as connection:
        row = connection.execute("SELECT COUNT(*) AS total FROM uploads").fetchone()
        if row and row["total"] > 0:
            return
        if not os.path.exists(MASTER_CSV):
            return
        with open(MASTER_CSV, "r", encoding="utf-8") as handle:
            text = handle.read()
        month = derive_month_from_filename(MASTER_CSV)
        connection.execute(
            "INSERT INTO uploads (month, csv_text) VALUES (?, ?)",
            (month, text),
        )


def list_months() -> List[str]:
    with get_db() as connection:
        rows = connection.execute(
            """
            SELECT month, MAX(created_at) AS last_created
            FROM uploads
            GROUP BY month
            ORDER BY last_created DESC
            """
        ).fetchall()
    return [row["month"] for row in rows]


def load_month_data(month: str) -> pd.DataFrame:
    with get_db() as connection:
        rows = connection.execute(
            "SELECT csv_text FROM uploads WHERE month = ? ORDER BY created_at",
            (month,),
        ).fetchall()
    if not rows:
        return pd.DataFrame()
    frames = [parse_csv_text(row["csv_text"]) for row in rows]
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


@app.get("/")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/upload")
def upload_csv():
    if "file" not in request.files:
        return jsonify({"error": "Archivo CSV requerido"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Nombre de archivo inválido"}), 400

    month = (request.form.get("month") or "").strip()
    if not month:
        return jsonify({"error": "Mes requerido"}), 400

    mode = (request.form.get("mode") or "replace").strip().lower()
    if mode not in {"replace", "append"}:
        return jsonify({"error": "Modo inválido"}), 400

    try:
        raw = file.read()
        if isinstance(raw, bytes):
            text = raw.decode("utf-8", errors="ignore")
        else:
            text = str(raw)
        new_df = parse_csv_text(text)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"CSV inválido: {exc}"}), 400

    if new_df.empty:
        return jsonify({"error": "CSV sin datos"}), 400

    with get_db() as connection:
        if mode == "replace":
            connection.execute("DELETE FROM uploads WHERE month = ?", (month,))
        connection.execute(
            "INSERT INTO uploads (month, csv_text) VALUES (?, ?)",
            (month, text),
        )

    return jsonify({
        "message": "Archivo recibido",
        "rows": len(new_df),
        "month": month,
        "mode": mode,
    })


@app.get("/months")
def months():
    months_list = list_months()
    selected = months_list[0] if months_list else ""
    return jsonify({"months": months_list, "selected": selected})


@app.get("/dashboard")
def dashboard():
    requested_month: Optional[str] = request.args.get("month")
    months_list = list_months()
    selected_month = requested_month or (months_list[0] if months_list else None)
    if not selected_month:
        return jsonify({
            "total_monto": 0,
            "total_refacturado": 0,
            "total_perdida": 0,
            "total_tickets": 0,
            "por_vendedor": [],
            "selected_month": "",
        })

    df = load_month_data(selected_month)
    if df.empty:
        return jsonify({
            "total_monto": 0,
            "total_refacturado": 0,
            "total_perdida": 0,
            "total_tickets": 0,
            "por_vendedor": [],
            "selected_month": selected_month,
        })

    if "MONTO DEVUELTO" not in df.columns:
        return jsonify({"error": "La columna 'MONTO DEVUELTO' no existe"}), 400

    monto_col = pd.to_numeric(df["MONTO DEVUELTO"], errors="coerce").fillna(0)
    total_monto = float(monto_col.sum())
    total_tickets = int(len(df))

    refact_column = None
    for candidate in ("MONTO REFACTURACION", "MONTO REFACTURADO"):
        if candidate in df.columns:
            refact_column = candidate
            break

    if refact_column:
        refact_col = pd.to_numeric(df[refact_column], errors="coerce").fillna(0)
        total_refacturado = float(refact_col.sum())
    else:
        total_refacturado = 0.0

    total_perdida = float(total_monto - total_refacturado)

    if "VENDEDOR" in df.columns:
        vendedor_clean = (
            df["VENDEDOR"]
            .astype(str)
            .str.strip()
            .str.replace(r"\s+", " ", regex=True)
        )
        grouped = (
            df.assign(_monto=monto_col, _vendedor=vendedor_clean)
            .groupby("_vendedor", dropna=False)
            .agg(monto=("_monto", "sum"), tickets=("_vendedor", "size"))
            .reset_index()
            .sort_values("monto", ascending=False)
        )
        por_vendedor: List[Dict[str, object]] = [
            {
                "vendedor": str(row["_vendedor"]),
                "monto": float(row["monto"]),
                "tickets": int(row["tickets"]),
            }
            for _, row in grouped.iterrows()
        ]
    else:
        por_vendedor = []

    return jsonify({
        "total_monto": total_monto,
        "total_refacturado": total_refacturado,
        "total_perdida": total_perdida,
        "total_tickets": total_tickets,
        "por_vendedor": por_vendedor,
        "selected_month": selected_month,
    })


init_db()
seed_db_if_empty()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
