export interface HealthResponse {
  status: string;
  db_connected: boolean;
  tables: {
    papers: number;
    trials: number;
    tweets: number;
    reddit: number;
    dosing: number;
    side_effects: number;
    mechanisms: number;
    conflicts: number;
  };
  synthesis_ready: boolean;
}

export interface MetaResponse {
  compound: string;
  aliases: string[];
  receptor_targets: string[];
  last_scrape: string | null;
  last_synthesis: string | null;
  version: string;
}

export interface DosingProtocol {
  id: number;
  source_type: string;
  source_id: string | null;
  compound: string | null;
  dose: string | null;
  frequency: string | null;
  duration: string | null;
  route: string | null;
  context: string | null;
  confidence: string | null;
}

export interface SideEffect {
  id: number;
  effect: string;
  severity: string | null;
  frequency: number;
  sources: string[] | null;
  description: string | null;
}

export interface Mechanism {
  id: number;
  mechanism: string;
  description: string;
  sources: string[] | null;
  confidence: string | null;
}

export interface Conflict {
  id: number;
  topic: string;
  source_a_type: string | null;
  source_a_id: string | null;
  source_a_claim: string | null;
  source_b_type: string | null;
  source_b_id: string | null;
  source_b_claim: string | null;
  description: string | null;
  resolution: string | null;
}

export interface SynthesisSummary {
  total_dosing_protocols: number;
  total_side_effects: number;
  total_mechanisms: number;
  total_conflicts: number;
  top_side_effects: Array<{
    name: string;
    frequency: number;
    max_severity: string | null;
  }>;
  receptor_coverage: Array<{ receptor: string; count: number }>;
  conflict_breakdown: { minor: number; major: number; critical: number };
  data_freshness: {
    oldest_paper: string | null;
    newest_paper: string | null;
    scrape_count: number;
  };
}

export interface StatsResponse {
  total_papers: number;
  total_trials: number;
  total_tweets: number;
  total_reddit_posts: number;
  total_dosing_protocols: number;
  total_side_effects: number;
}

export interface QueryRequest {
  question: string;
  max_context_rows?: number;
}

export interface QueryResponse {
  question: string;
  answer: string;
  sources_used: string[];
  confidence: number;
  domains_covered: string[];
  context_row_count: number;
  disclaimer: string;
}
