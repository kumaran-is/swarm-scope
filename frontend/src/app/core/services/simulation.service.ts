import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';

export interface SimulationRun {
  id: string;
  scenario_id: string;
  random_seed: number;
  status: string;
  current_tick: number;
  max_ticks: number;
  config: Record<string, unknown>;
  started_at?: string;
  completed_at?: string;
  created_at: string;
}

export interface Tick {
  id: string;
  tick_number: number;
  phase: string;
  active_agent_ids: string[];
  events: unknown[];
  kpi_values: Record<string, number>;
  duration_ms?: number;
}

@Injectable({ providedIn: 'root' })
export class SimulationService {
  private api = inject(ApiService);

  create(scenarioId: string, config: Record<string, unknown> = {}): Observable<SimulationRun> {
    return this.api.post<SimulationRun>('/simulations', {
      scenario_id: scenarioId,
      max_ticks: config['max_ticks'] ?? 15,
      config,
    });
  }

  get(id: string): Observable<SimulationRun> {
    return this.api.get<SimulationRun>(`/simulations/${id}`);
  }

  pause(id: string): Observable<unknown> {
    return this.api.post(`/simulations/${id}/pause`);
  }

  resume(id: string): Observable<unknown> {
    return this.api.post(`/simulations/${id}/resume`);
  }

  stop(id: string): Observable<unknown> {
    return this.api.post(`/simulations/${id}/stop`);
  }

  getTicks(id: string, skip = 0, limit = 50): Observable<Tick[]> {
    return this.api.get<Tick[]>(`/simulations/${id}/ticks`, { skip, limit });
  }

  getTick(id: string, tickNum: number): Observable<Tick> {
    return this.api.get<Tick>(`/simulations/${id}/ticks/${tickNum}`);
  }
}
