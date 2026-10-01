/** Load page JSON: prefer formal data/pages, fall back to sample/. */

export async function loadJson<T>(paths: string[]): Promise<T> {
  let lastErr: Error | null = null;
  for (const url of paths) {
    try {
      const res = await fetch(url);
      if (!res.ok) {
        lastErr = new Error(`无法加载 ${url}（${res.status}）`);
        continue;
      }
      return (await res.json()) as T;
    } catch (e) {
      lastErr = e instanceof Error ? e : new Error(String(e));
    }
  }
  throw lastErr ?? new Error('加载失败');
}

export function sampleOrPage(page: string, ticker?: string): string[] {
  if (page === 'watchlist' || page === 'sources') {
    return [`./data/pages/${page}.json`, `./sample/${page}.json`];
  }
  const t = ticker ?? 'MU';
  if (page === 'stockHeader') {
    return [`./data/pages/${t}/stockHeader.json`, `./sample/stockHeader.json`];
  }
  // P1+: financials prefers formal pages; other pages still sample-first until their phase
  if (page === 'financials') {
    return [`./data/pages/${t}/${page}.json`, `./sample/${page}.json`];
  }
  return [`./sample/${page}.json`, `./data/pages/${t}/${page}.json`];
}

export function addStockUrl(): string {
  const fromEnv = (import.meta as ImportMeta & { env?: Record<string, string> }).env
    ?.VITE_ADD_STOCK_URL;
  if (fromEnv) return fromEnv;
  return 'https://github.com/cool1990/stock_investing_dashboard/blob/main/config/watchlist.yaml';
}
