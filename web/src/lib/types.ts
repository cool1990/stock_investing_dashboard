export type MetricKind = 'eps' | 'rev';
export type GrowthKind = 'yoy' | 'pop';
export type PeriodKind = 'q' | 'y';
export type RevisionKey = 'FQ1-27' | 'FY27';

export interface ConsensusDetail {
  period: string;
  end: string;
  avg: number;
  low: number;
  high: number;
  n: number;
  year_ago: number;
  trend: { d7: number | null; d30: number | null; d60: number | null; d90: number | null };
  revisions: { up30: number | null; down30: number | null };
  guide: number | null;
}

export interface HistoryRow {
  period: string;
  release_date: string;
  consensus: number | null;
  actual: number;
  guide: number | null;
  next_day: number | null;
  secondary: number | null;
  pre_release_source?: string;
}

export interface HistoryBlock {
  q: HistoryRow[];
  y: HistoryRow[];
  stats_q: Record<string, string>;
  stats_y: Record<string, string>;
  note_q: string;
  note_y: string;
}

export interface ConsensusPage {
  meta: {
    ticker: string;
    name_en: string;
    name_zh: string;
    exchange: string;
    sector: string;
    updated_at_bj: string;
    latest_report: string;
    latest_report_date: string;
    release_timing: string;
    snapshot_note: string;
    quarter_labels: string[];
    header: Record<string, number | string | null>;
  };
  future: {
    years: string[];
    est_years: string[];
    eps: Record<string, Array<number | null>>;
    rev: Record<string, Array<number | null>>;
    detail: {
      eps: ConsensusDetail[];
      rev: ConsensusDetail[];
      eps_note: string;
      rev_note: string;
    };
    pe: {
      ttm_eps: number;
      ntm_eps: number | null;
      ntm_method: string;
      fy: Record<string, number | null>;
      last_close: number | null;
      note: string;
    };
  };
  revision: Record<
    string,
    {
      points: Array<[number, number]>;
      guide: number | null;
      up30: number;
      down30: number;
      n: number;
      note: string;
    }
  >;
  history: {
    eps: HistoryBlock;
    rev: HistoryBlock;
  };
}
