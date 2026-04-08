import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';

export interface Report {
  id: string;
  simulation_run_id: string;
  executive_summary?: string;
  narrative?: string;
  timeline: unknown[];
  influence_graph: { nodes: unknown[]; edges: unknown[] };
  key_findings?: unknown[];
  kpi_trajectories?: Record<string, unknown[]>;
  counterfactual_notes?: string;
  created_at: string;
}

@Injectable({ providedIn: 'root' })
export class ReportService {
  private api = inject(ApiService);

  generate(simId: string): Observable<{ status: string }> {
    return this.api.post<{ status: string }>(`/simulations/${simId}/report`, {});
  }

  get(simId: string): Observable<Report> {
    return this.api.get<Report>(`/simulations/${simId}/report`);
  }
}
