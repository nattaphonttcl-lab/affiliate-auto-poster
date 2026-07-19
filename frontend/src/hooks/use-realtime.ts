import { useEffect, useRef, useState } from "react";

type RealtimeMessage = {
  type: string;
  payload: unknown;
  timestamp: string;
};

export function useRealtime() {
  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState<RealtimeMessage[]>([]);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const base = import.meta.env.VITE_WS_URL;
    if (!base) {
      return;
    }

    const socket = new WebSocket(base);
    socketRef.current = socket;

    socket.onopen = () => setConnected(true);
    socket.onclose = () => setConnected(false);
    socket.onerror = () => setConnected(false);
    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as RealtimeMessage;
        setMessages((prev) => [payload, ...prev].slice(0, 50));
      } catch {
        setMessages((prev) => [
          {
            type: "raw",
            payload: event.data,
            timestamp: new Date().toISOString(),
          },
          ...prev,
        ]);
      }
    };

    return () => {
      socket.close();
    };
  }, []);

  return {
    connected,
    messages,
  };
}
