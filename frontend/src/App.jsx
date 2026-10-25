import { useEffect, useState } from "react";
import "./App.css";
import { api } from "./api";
import StartScreen from "./StartScreen";
import ChatScreen from "./ChatScreen";
import ReportScreen from "./ReportScreen";

const KEY = "eb_session";

function remember(id) {
  try { id ? localStorage.setItem(KEY, String(id)) : localStorage.removeItem(KEY); } catch { /* ignore */ }
}

export default function App() {
  const [screen, setScreen] = useState("loading"); // loading | start | chat | report
  const [session, setSession] = useState(null);    // { session_id, topic_id, topic_title, opening, turn_cap, restored? }
  const [report, setReport] = useState(null);

  useEffect(() => {
    let id = null;
    try { id = localStorage.getItem(KEY); } catch { /* ignore */ }
    if (!id) return setScreen("start");
    api.getSession(id)
      .then(async (st) => {
        if (st.status === "finished") {
          setReport(await api.getReport(st.session_id));
          setSession({ session_id: st.session_id, topic_id: st.topic_id, topic_title: st.topic_title });
          setScreen("report");
        } else {
          setSession({ ...st, restored: true });
          setScreen("chat");
        }
      })
      .catch(() => { remember(null); setScreen("start"); });
  }, []);

  function begin(s) {
    remember(s.session_id);
    setSession(s);
    setScreen("chat");
  }

  return (
    <main className="app">
      <header className="app-header">
        <h1>Explain-Back</h1>
        <p>Teach it to a curious beginner. Find out what you can't yet explain.</p>
      </header>

      {screen === "loading" && <p className="hint">Loading...</p>}
      {screen === "start" && <StartScreen onStarted={begin} />}
      {screen === "chat" && (
        <ChatScreen
          key={session.session_id}
          session={session}
          onReport={(r) => { setReport(r); setScreen("report"); }}
        />
      )}
      {screen === "report" && (
        <ReportScreen
          report={report}
          onRetry={async () => {
            const s = await api.createSession(session.topic_id);
            begin({ ...s, topic_id: session.topic_id });
          }}
          onNewTopic={() => { remember(null); setScreen("start"); }}
        />
      )}
    </main>
  );
}