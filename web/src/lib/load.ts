/** Load page JSON: prefer sample/ during P0, fall back to data/pages. */

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
    return [`./sample/${page}.json`, `./data/pages/${page}.json`];
  }
  const t = ticker ?? 'MU';
  if (page === 'stockHeader') {
    return [`./sample/stockHeader.json`, `./data/pages/${t}/stockHeader.json`];
  }
  return [`./sample/${page}.json`, `./data/pages/${t}/${page}.json`];
}

export function addStockUrl(): string {
  const fromEnv = (import.meta as ImportMeta & { env?: Record<string, string> }).env
    ?.VITE_ADD_STOCK_URL;
  if (fromEnv) return fromEnv;
  return 'https://github.com/cool1990/stock_investing_dashboard/blob/main/config/watchlist.yaml';
}
