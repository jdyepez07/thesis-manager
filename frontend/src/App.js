import React, { useState, useEffect } from "react";

function App() {
  const [name, setName] = useState("");
  const [repo, setRepo] = useState("");
  const [port, setPort] = useState("8080");
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [deploying, setDeploying] = useState(false);
  const [projects, setProjects] = useState([]);

  // Función auxiliar para extraer el puerto publicado desde el string de Ports
  const extractPort = (portsString) => {
    if (!portsString) return null;
    // Busca patrón hostPort->containerPort
    const match = portsString.match(/:(\d+)->/);
    return match ? match[1] : null;
  };


  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setStatus(null);
    try {
      const res = await fetch("http://localhost:5000/desplegar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nombre: name,
          link: repo,
          puerto: parseInt(port, 10)
        })
      });
      const data = await res.json();
      if (!res.ok) throw data;
      setDeploying(true);
      setStatus({ type: "info", data });
    } catch (err) {
      setStatus({ type: "error", err });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let interval;
    if (deploying) {
      interval = setInterval(async () => {
        try {
          const res = await fetch(`http://localhost:5000/status?nombre=${name}`);
          const data = await res.json();
          const text = JSON.stringify(data);
          if (text.includes("Up")) {
            setStatus({ type: "success", data });
            setDeploying(false);
            fetchProjects();
          } else if (text.includes("Exited") || text.includes("Error")) {
            setStatus({ type: "error", data });
            setDeploying(false);
          }
        } catch (err) {
          setStatus({ type: "error", err });
          setDeploying(false);
        }
      }, 5000);
    }
    return () => clearInterval(interval);
  }, [deploying, name]);

  const fetchProjects = async () => {
    try {
      const res = await fetch("http://localhost:5000/list");
      const data = await res.json();
      setProjects(data.containers || []);
    } catch (err) {
      console.error("Error cargando proyectos", err);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const stopProject = async (containerName) => {
    try {
      await fetch("http://localhost:5000/stop", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nombre: containerName })
      });
      fetchProjects();
    } catch (err) {
      console.error("Error deteniendo proyecto", err);
    }
  };

  return (
    <div style={{ background: "#1e1e1e", minHeight: "100vh", color: "#f0f0f0", padding: "2rem" }}>
      <div style={{ maxWidth: 900, margin: "0 auto", background: "#2c2c2c", padding: "2rem", borderRadius: 8 }}>
        <h1 style={{ textAlign: "center", marginBottom: "2rem" }}>Deploy Manager — Tesis / Proyectos GitHub</h1>

        {/* Formulario */}
        <form onSubmit={submit} style={{ marginBottom: 30 }}>
          <label>Nombre del proyecto</label><br />
          <input value={name} onChange={e => setName(e.target.value)} required
            style={{ width: "100%", padding: 8, marginBottom: 15, background: "#1e1e1e", color: "#fff", border: "1px solid #444", borderRadius: 4 }} />

          <label>Link del repositorio (github)</label><br />
          <input value={repo} onChange={e => setRepo(e.target.value)} required
            style={{ width: "100%", padding: 8, marginBottom: 15, background: "#1e1e1e", color: "#fff", border: "1px solid #444", borderRadius: 4 }} />

          <label>Puerto donde quieres visualizar</label><br />
          <input value={port} onChange={e => setPort(e.target.value)} required type="number" min="1" max="65535"
            style={{ width: 200, padding: 8, marginBottom: 15, background: "#1e1e1e", color: "#fff", border: "1px solid #444", borderRadius: 4 }} />

          <button type="submit" disabled={loading || deploying}
            style={{ padding: "8px 16px", background: "#3498db", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer" }}>
            {loading || deploying ? "Desplegando..." : "Desplegar"}
          </button>
        </form>

        {/* Mensajes UX */}
        {loading && (
          <div style={{ marginTop: 20, padding: 20, background: "#444", borderRadius: 8, textAlign: "center" }}>
            <p>Preparando despliegue...</p>
          </div>
        )}

        {deploying && (
          <div style={{ marginTop: 20, padding: 20, background: "#f39c12", borderRadius: 8, textAlign: "center", color: "#000" }}>
            <p>El proyecto se está construyendo y levantando, espera unos segundos...</p>
          </div>
        )}

        {!deploying && status && status.type === "success" && (
          <div style={{ marginTop: 20, padding: 20, background: "#2ecc71", borderRadius: 8, textAlign: "center", color: "#fff" }}>
            <p>Proyecto desplegado correctamente</p>
            <button
              style={{ marginTop: 10, padding: "6px 12px", background: "#27ae60", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer" }}
              onClick={() => window.open(`http://localhost:${port}`, "_blank")}
            >
              Abrir proyecto
            </button>
          </div>
        )}

        {!deploying && status && status.type === "error" && (
          <div style={{ marginTop: 20, padding: 20, background: "#e74c3c", borderRadius: 8, textAlign: "center", color: "#fff" }}>
            <p>Error al desplegar el proyecto</p>
          </div>
        )}

        {/* Tabla de proyectos activos */}
        <div style={{ marginTop: 40 }}>
          <h2>Proyectos levantados</h2>
          <table style={{ width: "100%", borderCollapse: "collapse", background: "#1e1e1e", color: "#fff" }}>
            <thead>
              <tr style={{ background: "#333" }}>
                <th style={{ padding: 10 }}>Nombre</th>
                <th style={{ padding: 10 }}>Imagen</th>
                <th style={{ padding: 10 }}>Estado</th>
                <th style={{ padding: 10 }}>Puertos</th>
                <th style={{ padding: 10 }}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {projects.length === 0 ? (
                <tr><td colSpan="5" style={{ textAlign: "center", padding: 15 }}>No hay proyectos activos</td></tr>
              ) : (
                projects.map((p, i) => {
                  const port = extractPort(p.Ports);
                  return (
                    <tr key={i} style={{ background: i % 2 === 0 ? "#2c2c2c" : "#1e1e1e" }}>
                      <td style={{ padding: 10 }}>{p.Names}</td>
                      <td style={{ padding: 10 }}>{p.Image}</td>
                      <td style={{ padding: 10 }}>{p.Status}</td>
                      <td style={{ padding: 10 }}>{p.Ports}</td>
                      <td style={{ padding: 10 }}>
                        <button
                          style={{ padding: "6px 12px", marginRight: 8, background: "#e74c3c", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer" }}
                          onClick={() => stopProject(p.Names)}
                        >
                          Detener
                        </button>
                        {port && (
                          <button
                            style={{ padding: "6px 12px", background: "#27ae60", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer" }}
                            onClick={() => window.open(`http://localhost:${port}`, "_blank")}
                          >
                            Abrir
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>

          </table>
        </div>
      </div>
    </div>
  );
}

export default App;
``