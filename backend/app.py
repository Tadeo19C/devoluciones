from __future__ import annotations

import io
import os
from typing import Dict, List

import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MASTER_CSV = os.path.join(BASE_DIR, "DEVOLUCIONES_TOTALES_FEBRERO_2026_3.csv")

app = Flask(__name__)
CORS(app)


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

    lines = text.splitlines()
    header_index = next(
        (idx for idx, line in enumerate(lines) if line.strip().startswith("FECHA,")),
        None,
    )
    if header_index is None:
        return pd.DataFrame()

    payload = "\n".join(lines[header_index:])
    return pd.read_csv(io.StringIO(payload))


def load_master() -> pd.DataFrame:
    return read_csv_with_header(MASTER_CSV)


def save_master(df: pd.DataFrame) -> None:
    df.to_csv(MASTER_CSV, index=False)


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

    try:
        new_df = read_csv_with_header(file)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"CSV inválido: {exc}"}), 400

    master_df = load_master()
    if master_df.empty:
        combined_df = new_df
    else:
        combined_df = pd.concat([master_df, new_df], ignore_index=True)

    save_master(combined_df)

    return jsonify({"message": "Archivo recibido", "rows": len(new_df)})


@app.get("/dashboard")
def dashboard():
    df = load_master()
    if df.empty:
        return jsonify({
            "total_monto": 0,
            "total_refacturado": 0,
            "total_perdida": 0,
            "total_tickets": 0,
            "por_vendedor": [],
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
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
