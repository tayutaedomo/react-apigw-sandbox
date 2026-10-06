import { useState } from 'react';

const cases: ProbeCase[] = [
  { id: 'not-found', label: '404：存在しないパス', path: '/missing' },
  { id: 'method', label: '405：未対応メソッド', path: '/hello', method: 'POST' },
  { id: 'validation', label: '422：入力検証エラー', path: '/errors/validation?value=wrong' },
  ...[400, 409, 418, 429, 500, 502, 503, 504].map(status => ({
    id: `http-${status}`, label: `${status}：明示的なエラー`, path: `/errors/http/${status}`,
  })),
  { id: 'unhandled', label: '500：未処理例外', path: '/errors/unhandled' },
  { id: 'response-validation', label: '500：レスポンス検証エラー', path: '/errors/response-validation' },
  { id: 'preflight-ok', label: 'プリフライト：GET を許可', path: '/errors/http/400', headers: { 'Content-Type': 'application/json' } },
  { id: 'preflight-header', label: 'プリフライト：未許可ヘッダー', path: '/errors/http/400', headers: { 'X-Probe': 'cors' } },
  { id: 'preflight-method', label: 'プリフライト：未許可メソッド', path: '/errors/http/400', method: 'PUT' },
];

type ProbeCase = { id: string; label: string; path: string; method?: string; headers?: Record<string, string> };
type Result = { status: number; body: string; requestId: string | null; retryAfter: string | null };

export function ErrorProbe({ apiBaseUrl }: { apiBaseUrl: string }) {
  const [selected, setSelected] = useState('not-found');
  const [result, setResult] = useState<Result | null>(null);
  const [failed, setFailed] = useState(false);
  const [loading, setLoading] = useState(false);

  async function runProbe() {
    const probe: ProbeCase = cases.find(item => item.id === selected)!;
    setLoading(true);
    setResult(null);
    setFailed(false);
    try {
      // HTTP エラーも本文を読み、CORS・ネットワークによる fetch の拒否と区別する。
      const response = await fetch(`${apiBaseUrl}${probe.path}`, {
        method: probe.method || 'GET', headers: probe.headers, credentials: 'omit',
      });
      setResult({
        status: response.status, body: await response.text(),
        requestId: response.headers.get('X-Request-Id'),
        retryAfter: response.headers.get('Retry-After'),
      });
    } catch {
      // fetch の例外だけでは CORS と通信障害を識別できないため、断定しない。
      setFailed(true);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section aria-labelledby="error-probe-heading">
      <h2 id="error-probe-heading">エラーレスポンスの CORS 検証</h2>
      <p>HTTP エラーの読み取りと、CORS・通信障害による読み取り失敗を確認します。</p>
      <label htmlFor="error-case">検証ケース</label>{' '}
      <select id="error-case" value={selected} disabled={loading} onChange={event => setSelected(event.target.value)}>
        {cases.map(item => <option key={item.id} value={item.id}>{item.label}</option>)}
      </select>{' '}
      <button type="button" onClick={runProbe} disabled={loading}>
        {loading ? '検証中…' : 'エラー API を呼び出す'}
      </button>
      <div aria-live="polite">
        {result && <div>
          <p>HTTP ステータス: {result.status}</p>
          <p>Request ID: {result.requestId || '取得できません'}</p>
          {result.retryAfter && <p>Retry-After: {result.retryAfter}</p>}
          <pre>{result.body}</pre>
        </div>}
        {failed && <p role="alert">レスポンスを読み取れませんでした。CORS 設定または通信状態を確認してください。</p>}
      </div>
    </section>
  );
}
