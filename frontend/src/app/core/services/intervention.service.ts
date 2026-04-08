import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';

export interface Intervention {
  id: string;
  simulation_run_id: string;
  type: string;
  payload: Record<string, unknown>;
  description?: string;
  target_tick?: number;
  applied_at_tick?: number;
  status: string;
  created_at: string;
}

@Injectable({ providedIn: 'root' })
export class InterventionService {
  private api = inject(ApiService);

  list(simId: string): Observable<Intervention[]> {
    return this.api.get<Intervention[]>(`/simulations/${simId}/interventions`);
  }

  create(simId: string, payload: Partial<Intervention>): Observable<Intervention> {
    return this.api.post<Intervention>(`/simulations/${simId}/interventions`, payload);
  }

  cancel(simId: string, ivId: string): Observable<void> {
    return this.api.delete<void>(`/simulations/${simId}/interventions/${ivId}`);
  }
}
