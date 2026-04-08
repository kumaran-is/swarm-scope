import { Component, OnInit, OnDestroy, inject, signal, effect } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { CommonModule } from '@angular/common';
import { Subscription, interval } from 'rxjs';
import { switchMap, takeWhile } from 'rxjs/operators';
import { WebSocketService } from '../../core/services/websocket.service';
import { SimulationService, Tick } from '../../core/services/simulation.service';

interface KpiEntry {
  name: string;
  value: number;
  trend: 'up' | 'down' | 'flat';
}

@Component({
  selector: 'app-live-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="dashboard">
      <header class="dash-header">
        <h1>Live Dashboard</h1>
        <span class="sim-id">Sim {{ simId }}</span>
        <span class="status-badge" [class.connected]="wsConnected()">
          {{ wsConnected() ? 'Live' : 'Disconnected' }}
        </span>
      </header>

      <section class="kpi-grid">
        @if (simStatus() === 'failed') {
          <div class="error-state">
            <p>Simulation failed to start. The backend could not load the world model or agents.</p>
            <p class="error-hint">Try re-generating agents and starting a new simulation.</p>
          </div>
        } @else if (simStatus() === 'pending' || simStatus() === 'running') {
          @for (kpi of kpis(); track kpi.name) {
            <div class="kpi-card">
              <div class="kpi-name">{{ kpi.name }}</div>
              <div class="kpi-value">{{ kpi.value | number: '1.1-1' }}</div>
              <div class="kpi-trend" [class]="kpi.trend">
                {{ kpi.trend === 'up' ? '↑' : kpi.trend === 'down' ? '↓' : '→' }}
              </div>
            </div>
          } @empty {
            <p class="empty-state">Waiting for simulation data... (status: {{ simStatus() }})</p>
          }
        } @else {
          @for (kpi of kpis(); track kpi.name) {
            <div class="kpi-card">
              <div class="kpi-name">{{ kpi.name }}</div>
              <div class="kpi-value">{{ kpi.value | number: '1.1-1' }}</div>
              <div class="kpi-trend" [class]="kpi.trend">
                {{ kpi.trend === 'up' ? '↑' : kpi.trend === 'down' ? '↓' : '→' }}
              </div>
            </div>
          } @empty {
            <p class="empty-state">Waiting for simulation data...</p>
          }
        }
      </section>

      <section class="mb-4">
        @if (lastTick(); as tick) {
          <div class="flex items-center gap-4 bg-base-200 rounded-lg px-4 py-3">
            <div class="flex items-center gap-2 font-mono font-bold text-primary">
              <span class="loading loading-ring loading-xs" [class.hidden]="simStatus() === 'completed'"></span>
              Tick {{ tick.tick_number }} / {{ maxTicks() }}
            </div>
            <div class="flex-1">
              <progress class="progress progress-primary w-full"
                [value]="tick.tick_number"
                [max]="maxTicks() || 1">
              </progress>
            </div>
            <span class="text-sm text-base-content/60">{{ tick.active_agent_ids?.length ?? 0 }} agents</span>
            <span class="text-sm text-base-content/60">{{ tick.events?.length ?? 0 }} events</span>
            <span class="text-sm text-base-content/60">{{ tick.duration_ms ?? 0 }}ms</span>
          </div>
        } @else {
          <div class="flex items-center gap-3 bg-base-200 rounded-lg px-4 py-3 text-base-content/50">
            <span class="loading loading-ring loading-xs"></span>
            @if (simStatus() === 'pending') {
              Preparing agents... simulation will start shortly
            } @else if (simStatus() === 'running') {
              Running — waiting for first tick data...
            } @else {
              Waiting for first tick...
            }
          </div>
        }
      </section>

      <div class="flex gap-3 mb-4">
        <a class="btn btn-outline btn-sm" [routerLink]="['/simulations', simId, 'report']">View Report</a>
        <a class="btn btn-ghost btn-sm" [routerLink]="['/simulations', simId, 'intervene']">Interventions</a>
        <a class="btn btn-ghost btn-sm" [routerLink]="['/simulations', simId, 'chat']">Agent Chat</a>
      </div>

      <section class="event-log">
        <h2>Recent Events</h2>
        <ul>
          @for (event of recentEvents(); track $index) {
            <li class="event-item">{{ event }}</li>
          } @empty {
            <li class="empty-state">No events yet.</li>
          }
        </ul>
      </section>
    </div>
  `,
  styles: [`
    .dashboard { padding: 1.5rem; }
    .dash-header { display: flex; align-items: center; gap: 1rem; margin-bottom: 1.5rem; }
    .sim-id { color: #888; font-size: 0.9rem; }
    .status-badge { padding: 0.25rem 0.75rem; border-radius: 999px; background: #ccc; font-size: 0.8rem; }
    .status-badge.connected { background: #4caf50; color: #fff; }
    .kpi-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
    .kpi-card { background: #1e1e2e; border-radius: 8px; padding: 1rem; text-align: center; }
    .kpi-name { font-size: 0.8rem; color: #888; margin-bottom: 0.25rem; }
    .kpi-value { font-size: 1.8rem; font-weight: 700; }
    .kpi-trend { font-size: 1.2rem; }
    .kpi-trend.up { color: #4caf50; }
    .kpi-trend.down { color: #f44336; }
    .kpi-trend.flat { color: #888; }
    .tick-row { display: flex; gap: 2rem; background: #1e1e2e; padding: 0.75rem 1rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.9rem; }
    .event-log h2 { font-size: 1rem; margin-bottom: 0.5rem; }
    .event-log ul { list-style: none; padding: 0; max-height: 300px; overflow-y: auto; }
    .event-item { padding: 0.4rem 0.75rem; border-bottom: 1px solid #2a2a3e; font-size: 0.85rem; font-family: monospace; }
    .empty-state { color: #888; font-style: italic; }
    .error-state { grid-column: 1 / -1; background: #3e1e1e; border: 1px solid #f44336; border-radius: 8px; padding: 1.5rem; color: #ff8a80; }
    .error-hint { font-size: 0.85rem; color: #888; margin-top: 0.5rem; }
  `],
})
export class LiveDashboardComponent implements OnInit, OnDestroy {
  private route = inject(ActivatedRoute);
  private ws = inject(WebSocketService);
  private simService = inject(SimulationService);

  simId = '';
  kpis = signal<KpiEntry[]>([]);
  lastTick = signal<Tick | null>(null);
  recentEvents = signal<string[]>([]);
  simStatus = signal<string>('pending');
  maxTicks = signal<number>(15);
  wsConnected = this.ws.connected;

  private prevKpiValues: Record<string, number> = {};
  private statusPollSub?: Subscription;

  constructor() {
    effect(() => {
      const msg = this.ws.lastMessage();
      if (msg?.type === 'tick_complete' && msg.tick != null) {
        const d = msg.data as Record<string, unknown>;
        const agentCount = Number(d['active_agent_count'] ?? 0);
        const eventCount = Number(d['event_count'] ?? 0);
        const durationMs = Number(d['duration_ms'] ?? 0);
        const kpiValues = (d['kpi_values'] as Record<string, number>) ?? {};
        // Backend broadcasts a summary — normalize to Tick shape
        const tick: Tick = {
          id: '',
          tick_number: msg.tick,
          phase: 'complete',
          active_agent_ids: new Array(agentCount).fill(''),
          events: [`Tick ${msg.tick}: ${agentCount} agents acted, ${eventCount} events in ${durationMs}ms`],
          kpi_values: kpiValues,
          duration_ms: durationMs,
        };
        this.processTick(tick);
      }
    });
  }

  ngOnInit(): void {
    this.simId = this.route.snapshot.paramMap.get('id') ?? '';
    this.ws.connect(this.simId);

    // Load tick history
    this.simService.getTicks(this.simId).subscribe({
      next: (ticks) => {
        if (ticks.length > 0) {
          this.processTick(ticks[ticks.length - 1]);
        }
      },
      error: (err) => console.error('Failed to load ticks', err),
    });

    // Poll simulation status — stop once terminal state reached
    this.statusPollSub = interval(3000).pipe(
      switchMap(() => this.simService.get(this.simId)),
      takeWhile((run) => run.status !== 'completed' && run.status !== 'failed', true),
    ).subscribe({
      next: (run) => { this.simStatus.set(run.status); this.maxTicks.set(run.max_ticks); },
      error: () => {},
    });
  }

  ngOnDestroy(): void {
    this.ws.disconnect();
    this.statusPollSub?.unsubscribe();
  }

  private processTick(tick: Tick): void {
    this.lastTick.set(tick);
    const kpiData = tick.kpi_values ?? {};
    const entries: KpiEntry[] = Object.entries(kpiData).map(([name, value]) => {
      const prev = this.prevKpiValues[name];
      const trend: 'up' | 'down' | 'flat' =
        prev === undefined ? 'flat' : value > prev ? 'up' : value < prev ? 'down' : 'flat';
      return { name, value, trend };
    });
    this.prevKpiValues = { ...kpiData };
    this.kpis.set(entries);

    const events = (tick.events as string[] | null) ?? [];
    this.recentEvents.update((prev) => [...events, ...prev].slice(0, 50));
  }
}
