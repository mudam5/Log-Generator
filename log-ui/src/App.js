import React, { useState, useEffect } from "react";
import axios from "axios";
import { PieChart, Pie, Cell, Tooltip, Legend } from "recharts";

const API = "/api";
const TYPE_COLORS = { auth: "#007bff", payment: "#28a745", system: "#ffc107", application: "#dc3545" };

function App() {
  const [logs, setLogs] = useState([]);
  const [counts, setCounts] = useState({});
  const [loading, setLoading] = useState(false);
  const [filterType, setFilterType] = useState("all");
  const [filterLevel, setFilterLevel] = useState("all");
  const [searchText, setSearchText] = useState("");
  const [timeRange, setTimeRange] = useState("all");

  const fetchData = async () => {
    setLoading(true);
    try {
      const [logsRes, countsRes] = await Promise.all([
        axios.get(`${API}/logs?limit=500`),
        axios.get(`${API}/analyze`)
      ]);
      setLogs(logsRes.data.logs || []);
      setCounts(countsRes.data.counts || {});
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  useEffect(() => {
    fetchData();
    const id = setInterval(fetchData, 30000);
    return () => clearInterval(id);
  }, []);

  const chartData = Object.entries(counts).map(([name, value]) => ({ name, value }));
  const filtered = logs.filter((l) => {
    const typeOk = filterType === "all" || l.type === filterType;
    const levelOk = filterLevel === "all" || l.level === filterLevel;
    const searchOk = !searchText || (l.message || "").toLowerCase().includes(searchText.toLowerCase());
    let timeOk = true;
    if (timeRange !== "all") {
      const t = new Date(l.timestamp).getTime();
      const now = Date.now();
      if (timeRange === "5m") timeOk = now - t <= 5 * 60 * 1000;
      else if (timeRange === "1h") timeOk = now - t <= 60 * 60 * 1000;
      else if (timeRange === "24h") timeOk = now - t <= 24 * 60 * 60 * 1000;
    }
    return typeOk && levelOk && searchOk && timeOk;
  });

  return (
    <div style={{ padding: 20 }}>
      <h2>📊 Log Dashboard</h2>
      <div style={{ marginBottom: 12 }}>
        <button onClick={fetchData} disabled={loading}>{loading ? "Refreshing..." : "🔄 Refresh"}</button>
        <select value={filterType} onChange={(e)=>setFilterType(e.target.value)} style={{ marginLeft: 8 }}>
          <option value="all">All Types</option><option value="auth">Auth</option><option value="payment">Payment</option><option value="system">System</option><option value="application">Application</option>
        </select>
        <select value={filterLevel} onChange={(e)=>setFilterLevel(e.target.value)} style={{ marginLeft: 8 }}>
          <option value="all">All Levels</option><option value="INFO">INFO</option><option value="DEBUG">DEBUG</option><option value="WARN">WARN</option><option value="ERROR">ERROR</option>
        </select>
        <select value={timeRange} onChange={(e)=>setTimeRange(e.target.value)} style={{ marginLeft: 8 }}>
          <option value="all">All time</option><option value="5m">Last 5 min</option><option value="1h">Last 1 hour</option><option value="24h">Last 24 hours</option>
        </select>
        <input placeholder="Search message..." value={searchText} onChange={e=>setSearchText(e.target.value)} style={{ marginLeft: 8, padding: 4 }} />
      </div>

      <div style={{ display: "flex", gap: 24 }}>
        <div style={{ width: 420 }}>
          <h4>Distribution</h4>
          <PieChart width={400} height={300}>
            <Pie data={chartData} dataKey="value" nameKey="name" outerRadius={120} label>
              {chartData.map((entry, idx)=> (<Cell key={idx} fill={TYPE_COLORS[entry.name] || "#888"} />))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        </div>

        <div style={{ flex: 1 }}>
          <h4>Logs ({filtered.length})</h4>
          <div style={{ maxHeight: 520, overflow: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead><tr style={{ background: "#eee" }}><th style={{ padding: 8 }}>ID</th><th style={{ padding: 8 }}>Type</th><th style={{ padding: 8 }}>Level</th><th style={{ padding: 8 }}>Message</th><th style={{ padding: 8 }}>Timestamp</th></tr></thead>
              <tbody>
                {filtered.map((l,i)=>(
                  <tr key={i} style={{ color: TYPE_COLORS[l.type] || "#000" }}>
                    <td style={{ padding: 8 }}>{l.id}</td>
                    <td style={{ padding: 8 }}>{l.type}</td>
                    <td style={{ padding: 8 }}>{l.level}</td>
                    <td style={{ padding: 8 }}>{l.message}</td>
                    <td style={{ padding: 8 }}>{new Date(l.timestamp).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filtered.length === 0 && <div style={{ color: "#666", marginTop: 8 }}>No logs match filters.</div>}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
