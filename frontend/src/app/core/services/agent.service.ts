import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';

export interface Agent {
  id: string;
  simulation_run_id: string;
  name: string;
  role: string;
  faction?: string;
  traits: Record<string, unknown>;
  goals: string[];
  resources: Record<string, number>;
  relationships: Record<string, unknown>;
  working_memory: Record<string, unknown>;
  episodic_memory: unknown[];
  semantic_memory: Record<string, unknown>;
  activation_score: number;
  is_active: boolean;
  is_chat_enabled: boolean;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

@Injectable({ providedIn: 'root' })
export class AgentService {
  private api = inject(ApiService);

  list(simId: string): Observable<Agent[]> {
    return this.api.get<Agent[]>(`/simulations/${simId}/agents`);
  }

  get(simId: string, agentId: string): Observable<Agent> {
    return this.api.get<Agent>(`/simulations/${simId}/agents/${agentId}`);
  }

  chat(simId: string, agentId: string, message: string): Observable<{ message: string }> {
    return this.api.post<{ message: string }>(
      `/simulations/${simId}/agents/${agentId}/chat`,
      { message }
    );
  }
}
