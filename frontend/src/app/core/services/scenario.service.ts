import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';

export interface Scenario {
  id: string;
  name: string;
  description?: string;
  domain: string;
  config: Record<string, unknown>;
  status: string;
  source_file_path?: string;
  created_at: string;
  updated_at: string;
}

@Injectable({ providedIn: 'root' })
export class ScenarioService {
  private api = inject(ApiService);

  list(): Observable<Scenario[]> {
    return this.api.get<Scenario[]>('/scenarios');
  }

  get(id: string): Observable<Scenario> {
    return this.api.get<Scenario>(`/scenarios/${id}`);
  }

  create(formData: FormData): Observable<Scenario> {
    return this.api.postForm<Scenario>('/scenarios', formData);
  }

  update(id: string, updates: Partial<Scenario>): Observable<Scenario> {
    return this.api.put<Scenario>(`/scenarios/${id}`, updates);
  }

  delete(id: string): Observable<void> {
    return this.api.delete<void>(`/scenarios/${id}`);
  }

  compile(id: string): Observable<{ status: string }> {
    return this.api.post<{ status: string }>(`/scenarios/${id}/compile`);
  }

  generateAgents(id: string, count: number = 10): Observable<{ status: string }> {
    return this.api.post<{ status: string }>(`/scenarios/${id}/generate-agents?count=${count}`);
  }

  getWorldModel(id: string): Observable<unknown> {
    return this.api.get(`/scenarios/${id}/world`);
  }

  updateWorldModel(id: string, update: unknown): Observable<unknown> {
    return this.api.put(`/scenarios/${id}/world`, update);
  }

  getKnowledgeGraph(id: string): Observable<{ nodes: unknown[]; edges: unknown[] }> {
    return this.api.get(`/scenarios/${id}/knowledge-graph`);
  }
}
