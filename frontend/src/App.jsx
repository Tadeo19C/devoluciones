import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import logo from "./assets/sinsa-logo.png";
import "./App.css";

const API_BASE =
  import.meta.env.VITE_API_BASE ||
  `${window.location.protocol}//${window.location.hostname}:5000`;

export default function App() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [dashboard, setDashboard] = useState({
    total_monto: 0,
    total_refacturado: 0,
    total_tickets: 0,
    por_vendedor: [],
  });
  const [error, setError] = useState("");
  const [selectedVendedor, setSelectedVendedor] = useState("");

  const formatCurrency = (value) =>
    new Intl.NumberFormat("es-NI", {
      style: "currency",
      currency: "NIO",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value || 0);

  const formattedTotal = useMemo(() => {
    return formatCurrency(dashboard.total_monto);
  }, [dashboard.total_monto]);

  const formattedRefacturado = useMemo(() => {
    return formatCurrency(dashboard.total_refacturado);
  }, [dashboard.total_refacturado]);

  const topVendedores = useMemo(() => {
    return [...dashboard.por_vendedor].slice(0, 5);
  }, [dashboard.por_vendedor]);

  useEffect(() => {
    if (!dashboard.por_vendedor.length) {
      setSelectedVendedor("");
      return;
    }
    const hasSelection = dashboard.por_vendedor.some(
      (item) => item.vendedor === selectedVendedor
    );
    if (!selectedVendedor || !hasSelection) {
      setSelectedVendedor(dashboard.por_vendedor[0].vendedor);
    }
  }, [dashboard.por_vendedor, selectedVendedor]);

  const selectedVendor = useMemo(() => {
    if (!selectedVendedor) return null;
    return dashboard.por_vendedor.find(
      (item) => item.vendedor === selectedVendedor
    );
  }, [dashboard.por_vendedor, selectedVendedor]);

  const topPercent = useMemo(() => {
    if (!selectedVendor || !dashboard.total_monto) return 0;
    return Math.min((selectedVendor.monto / dashboard.total_monto) * 100, 100);
  }, [selectedVendor, dashboard.total_monto]);

  const fetchDashboard = async () => {
    try {
      setError("");
      const response = await fetch(`${API_BASE}/dashboard`);
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Error al cargar dashboard");
      }
      setDashboard(data);
    } catch (err) {
      setError(err.message || "Error desconocido");
    }
  };

  useEffect(() => {
    fetchDashboard();
  }, []);

  const handleUpload = async (event) => {
    event.preventDefault();
    if (!file) {
      setError("Selecciona un archivo CSV");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
      setLoading(true);
      setError("");
      const response = await fetch(`${API_BASE}/upload`, {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Error al subir CSV");
      }
      await fetchDashboard();
      setFile(null);
    } catch (err) {
      setError(err.message || "Error desconocido");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <header className="app__header">
        <div className="brand">
          <img src={logo} alt="SINSA" className="brand__logo" />
          <div>
            <h1>Control de Devoluciones</h1>
            <p>
              Subes el CSV diario y revisa el estado actualizado.
              <span className="badge">Mes por defecto: Febrero</span>
            </p>
          </div>
        </div>
        <form className="upload" onSubmit={handleUpload}>
          <input
            type="file"
            accept=".csv"
            onChange={(event) => setFile(event.target.files?.[0] || null)}
          />
          <button type="submit" disabled={loading}>
            {loading ? "Subiendo..." : "Subir CSV"}
          </button>
        </form>
      </header>

      {error && <div className="error">{error}</div>}

      <section className="metrics">
        <div className="card">
          <span>Monto Total Devuelto</span>
          <strong>{formattedTotal}</strong>
        </div>
        <div className="card">
          <span>Monto Refacturado</span>
          <strong>{formattedRefacturado}</strong>
        </div>
        <div className="card">
          <span>Total de Tickets</span>
          <strong>{dashboard.total_tickets}</strong>
        </div>
        <div className="card card--highlight">
          <span>Vendedor seleccionado (mes actual)</span>
          <div className="card__select">
            <strong>{selectedVendor ? selectedVendor.vendedor : "-"}</strong>
            <select
              value={selectedVendedor}
              onChange={(event) => setSelectedVendedor(event.target.value)}
              disabled={!dashboard.por_vendedor.length}
              aria-label="Selecciona un vendedor"
            >
              {dashboard.por_vendedor.map((item) => (
                <option key={item.vendedor} value={item.vendedor}>
                  {item.vendedor}
                </option>
              ))}
            </select>
          </div>
          <div className="card__meta">
            <small>{selectedVendor ? `${selectedVendor.tickets} tickets` : ""}</small>
            <em>{selectedVendor ? formatCurrency(selectedVendor.monto) : ""}</em>
          </div>
          <div className="meter">
            <div className="meter__fill" style={{ width: `${topPercent}%` }} />
          </div>
          <small className="meter__label">
            {selectedVendor ? `${topPercent.toFixed(1)}% del total` : ""}
          </small>
        </div>
      </section>

      <section className="chart">
        <div className="chart__header">
          <h2>Montos devueltos por vendedor</h2>
          <span>Top 5 con tickets</span>
        </div>
        <div className="chart__grid">
          <div className="chart__container">
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={dashboard.por_vendedor} margin={{ left: 12, right: 12 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis dataKey="vendedor" tick={{ fill: "#94a3b8" }} />
                <YAxis tick={{ fill: "#94a3b8" }} />
                <Tooltip
                  formatter={(value) => formatCurrency(value)}
                  contentStyle={{ background: "#0f1c15", borderRadius: 8, border: "1px solid #1f2a22" }}
                  labelStyle={{ color: "#e2e8f0" }}
                />
                <Bar dataKey="monto" fill="#22c55e" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="top">
            <h3>Top vendedores</h3>
            <ul>
              {topVendedores.map((item) => (
                <li key={item.vendedor}>
                  <div>
                    <strong>{item.vendedor}</strong>
                    <span>{item.tickets} tickets</span>
                  </div>
                  <em>{formatCurrency(item.monto)}</em>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>
    </div>
  );
}
