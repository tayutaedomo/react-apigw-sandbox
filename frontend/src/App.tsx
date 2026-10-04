import { useState } from 'react';

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

type HelloResponse = { message: string };

export function App() {
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function fetchHello() {
    setLoading(true);
    setMessage(null);
    setError(null);

    try {
      const response = await fetch(`${apiBaseUrl}/hello`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const body: HelloResponse = await response.json();
      setMessage(body.message);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <h1>Hello World</h1>
      <p>React + FastAPI sandbox</p>
      <button type="button" onClick={fetchHello} disabled={loading}>
        {loading ? '取得中…' : 'API を呼び出す'}
      </button>
      <div aria-live="polite">
        {message && <p>API: {message}</p>}
      </div>
      {error && <p role="alert">API 呼び出しに失敗しました: {error}</p>}
    </main>
  );
}
