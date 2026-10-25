import { useState } from "react";
import "./App.css";
import StartScreen from "./StartScreen";
import ChatScreen from "./ChatScreen";
import ReportScreen from "./ReportScreen";

export default function App() {
  const [screen, setScreen] = useState("start"); // start | chat | report
  const [session, setSession] = useState(null);  // { session_id, topic_id, topic_title, opening, turn_cap }
  const [report, setReport] = useState(null);

  return (
    <main className="app">
      <header className="app-header">
        <h1>Explain-Back</h1>
        <p>Teach it to a curious beginner. Find out what you can't yet explain.</p>
      </header>

      {screen === "start" && (
        <StartScreen
          onStarted={(s) => {
            setSession(s);
            setScreen("chat");
          }}
        />
      )}
      {screen === "chat" && (
        <ChatScreen
          key={session.session_id}
          session={session}
          onReport={(r) => {
            setReport(r);
            setScreen("report");
          }}
        />
      )}
      {screen === "report" && (
        <ReportScreen
          report={report}
          onRetry={async () => {
            const { api } = await import("./api");
            const s = await api.createSession(session.topic_id);
            setSession({ ...s, topic_id: session.topic_id });
            setScreen("chat");
          }}
          onNewTopic={() => setScreen("start")}
        />
      )}
    </main>
  );
}