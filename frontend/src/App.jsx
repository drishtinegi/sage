import { useEffect, useState } from "react";

export default function App() {
  const [status, setStatus] = useState("checking...");

  useEffect(() => {
    fetch(`${import.meta.env.VITE_API_URL}/health`)
      .then((r) => r.json())
      .then((d) => setStatus(`API ${d.status}, DB ${d.db}`))
      .catch(() => setStatus("API unreachable"));
  }, []);

  return <h1>Explain-Back: {status}</h1>;
}