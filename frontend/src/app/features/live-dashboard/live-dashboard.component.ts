import { Component, OnInit, OnDestroy, inject, signal, effect } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { CommonModule } from '@angular/common';
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
  imports: [CommonModule],
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
      </section>

      <section class="tick-info">
        @if (lastTick(); as tick) {
          <div class="tick-row">
            <span>Tick {{ tick.tick_number }}</span>
            <span>Active agents: {{ tick.active_agent_ids?.length ?? 0 }}</span>
            <span>Events: {{ tick.events?.length ?? 0 }}</span>
          </div>
        }
      </section>

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
  wsConnected = this.ws.connected;

  private prevKpiValues: Record<string, number> = {};

  constructor() {
    effect(() => {
      const msg = this.ws.lastMessage();
      if (msg?.type === 'tick_complete') {
        this.processTick(msg.data as Tick);
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
  }

  ngOnDestroy(): void {
    this.ws.disconnect();
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
