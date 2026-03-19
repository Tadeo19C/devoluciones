from __future__ import annotations

import io
import sqlite3
import sys
from pathlib import Path

import pandas as pd


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def assert_ok(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def main() -> None:
    # Importing app gives us the Flask test client and the same DB logic used in runtime.
    import app as backend_app

    db_path = Path(backend_app.DB_PATH)
    assert_ok(db_path.exists(), f"No existe la BD en {db_path}")

    client = backend_app.app.test_client()

    month_csv = "QA CSV"
    month_xlsx = "QA XLSX"

    with backend_app.get_db() as connection:
        connection.execute(
            "DELETE FROM uploads WHERE month IN (?, ?)",
            (month_csv, month_xlsx),
        )

    sample_df = pd.DataFrame(
        {
            "FECHA": ["2026-03-01", "2026-03-02", "2026-03-03"],
            "MONTO DEVUELTO": [100.0, 200.0, 50.0],
            "MONTO REFACTURACION": [20.0, 40.0, 0.0],
            "VENDEDOR": ["Ana", "Luis", "Ana"],
        }
    )

    csv_payload = sample_df.to_csv(index=False).encode("utf-8")
    upload_csv = client.post(
        "/upload",
        data={
            "file": (io.BytesIO(csv_payload), "prueba.csv"),
            "month": month_csv,
            "mode": "replace",
        },
        content_type="multipart/form-data",
    )
    assert_ok(upload_csv.status_code == 200, f"Upload CSV fallo: {upload_csv.data}")

    excel_bytes = io.BytesIO()
    sample_df.to_excel(excel_bytes, index=False)
    excel_bytes.seek(0)
    upload_xlsx = client.post(
        "/upload",
        data={
            "file": (excel_bytes, "prueba.xlsx"),
            "month": month_xlsx,
            "mode": "replace",
        },
        content_type="multipart/form-data",
    )
    assert_ok(upload_xlsx.status_code == 200, f"Upload XLSX fallo: {upload_xlsx.data}")

    months_response = client.get("/months")
    assert_ok(months_response.status_code == 200, "Endpoint /months no responde 200")
    months_data = months_response.get_json() or {}
    months = months_data.get("months", [])
    assert_ok(month_csv in months, "No aparece mes de prueba CSV en /months")
    assert_ok(month_xlsx in months, "No aparece mes de prueba XLSX en /months")

    dashboard_csv = client.get("/dashboard", query_string={"month": month_csv})
    dashboard_xlsx = client.get("/dashboard", query_string={"month": month_xlsx})
    assert_ok(dashboard_csv.status_code == 200, "Dashboard CSV no responde 200")
    assert_ok(dashboard_xlsx.status_code == 200, "Dashboard XLSX no responde 200")

    csv_data = dashboard_csv.get_json() or {}
    xlsx_data = dashboard_xlsx.get_json() or {}
    assert_ok(csv_data.get("total_tickets") == 3, "CSV no cargo 3 tickets")
    assert_ok(xlsx_data.get("total_tickets") == 3, "XLSX no cargo 3 tickets")
    assert_ok(float(csv_data.get("total_monto", 0)) == 350.0, "CSV total_monto inesperado")
    assert_ok(float(xlsx_data.get("total_monto", 0)) == 350.0, "XLSX total_monto inesperado")

    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT month, COUNT(*) AS registros, SUM(LENGTH(csv_text)) AS bytes_totales
            FROM uploads
            WHERE month IN (?, ?)
            GROUP BY month
            ORDER BY month
            """,
            (month_csv, month_xlsx),
        ).fetchall()

    assert_ok(len(rows) == 2, "No se guardaron ambos meses en SQLite")
    for month, records, total_bytes in rows:
        assert_ok(records >= 1, f"No hay registros para {month}")
        assert_ok((total_bytes or 0) > 0, f"csv_text vacio para {month}")

    print("PASS: CSV y XLSX suben, actualizan dashboard y se guardan en SQLite.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {exc}")
        sys.exit(1)