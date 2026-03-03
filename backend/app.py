from __future__ import annotations

import os
from typing import Dict, List

import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MASTER_CSV = os.path.join(BASE_DIR, "Devoluciones_Febrero_Consolidado_Hasta_23.csv")

app = Flask(__name__)
CORS(app)


def load_master() -> pd.DataFrame:
    if not os.path.exists(MASTER_CSV):
        return pd.DataFrame()
    return pd.read_csv(MASTER_CSV)


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
        new_df = pd.read_csv(file)
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
            "total_tickets": 0,
            "por_vendedor": [],
        })

    if "MONTO DEVUELTO" not in df.columns:
        return jsonify({"error": "La columna 'MONTO DEVUELTO' no existe"}), 400

    monto_col = pd.to_numeric(df["MONTO DEVUELTO"], errors="coerce").fillna(0)
    total_monto = float(monto_col.sum())
    total_tickets = int(len(df))

    if "MONTO REFACTURACION" in df.columns:
        refact_col = pd.to_numeric(df["MONTO REFACTURACION"], errors="coerce").fillna(0)
        total_refacturado = float(refact_col.sum())
    else:
        total_refacturado = 0.0

    if "VENDEDOR" in df.columns:
        grouped = (
            df.assign(_monto=monto_col)
            .groupby("VENDEDOR", dropna=False)
            .agg(monto=("_monto", "sum"), tickets=("VENDEDOR", "size"))
            .reset_index()
            .sort_values("monto", ascending=False)
        )
        por_vendedor: List[Dict[str, object]] = [
            {
                "vendedor": str(row["VENDEDOR"]),
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
        "total_tickets": total_tickets,
        "por_vendedor": por_vendedor,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
