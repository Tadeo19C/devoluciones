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
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem("theme") || "dark";
  });
  const [dashboard, setDashboard] = useState({
    total_monto: 0,
    total_refacturado: 0,
    total_perdida: 0,
    total_tickets: 0,
    por_vendedor: [],
  });
  const [error, setError] = useState("");
  const [selectedVendedor, setSelectedVendedor] = useState("");

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("theme", theme);
  }, [theme]);

  const formatCurrency = (value) =>
    new Intl.NumberFormat("es-NI", {
      style: "currency",
      currency: "NIO",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value || 0);

  const formattedRefacturado = useMemo(() => {
    return formatCurrency(dashboard.total_refacturado);
  }, [dashboard.total_refacturado]);

  const formattedTotalMonto = useMemo(() => {
    return formatCurrency(dashboard.total_monto);
  }, [dashboard.total_monto]);

  const rawPerdida = useMemo(() => {
    const fallback = dashboard.total_monto - dashboard.total_refacturado;
    const value = dashboard.total_perdida ?? fallback;
    return Number.isFinite(value) ? value : 0;
  }, [dashboard.total_monto, dashboard.total_refacturado, dashboard.total_perdida]);

  const formattedPerdida = useMemo(() => {
    return formatCurrency(rawPerdida);
  }, [rawPerdida]);

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
          <button
            type="button"
            className="theme-toggle"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          >
            {theme === "dark" ? "Tono claro" : "Tono oscuro"}
          </button>
        </form>
      </header>

      {error && <div className="error">{error}</div>}

      <a
        className="cta"
        href="https://docs.google.com/spreadsheets/d/10goNa5Ghkto2bhzamjK4nitiZtt04WAOfORwCr53Y6E/edit?usp=sharing"
        target="_blank"
        rel="noreferrer"
      >
        <div>
          <span>Excel maestro con toda la data</span>
          <strong>Ver hoja en Google Sheets</strong>
        </div>
        <span className="cta__arrow" aria-hidden="true">→</span>
      </a>

      <section className="metrics">
        <div className="card">
          <span>Total de devoluciones</span>
          <strong>{formattedTotalMonto}</strong>
        </div>
        <div className="card">
          <span>Total de perdida</span>
          <strong>{formattedPerdida}</strong>
        </div>
        <div className="card">
          <span>Refacturado final</span>
          <strong>{formattedRefacturado}</strong>
        </div>
        <div className="card card--tickets">
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
                <CartesianGrid strokeDasharray="3 3" stroke="var(--grid)" />
                <XAxis dataKey="vendedor" tick={{ fill: "var(--text-muted)" }} />
                <YAxis tick={{ fill: "var(--text-muted)" }} />
                <Tooltip
                  formatter={(value) => formatCurrency(value)}
                  contentStyle={{
                    background: "var(--tooltip-bg)",
                    borderRadius: 8,
                    border: "1px solid var(--tooltip-border)",
                  }}
                  labelStyle={{ color: "var(--text)" }}
                />
                <Bar dataKey="monto" fill="var(--accent)" radius={[6, 6, 0, 0]} />
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
