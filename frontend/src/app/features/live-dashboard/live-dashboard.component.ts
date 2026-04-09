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
    <div class="animate-fade-up" style="padding: 1.5rem;">
      <!-- Header -->
      <header class="flex items-center gap-3 mb-6 flex-wrap">
        <h1 class="text-2xl font-bold tracking-tight" style="color: var(--ss-text-primary);">Live Dashboard</h1>
        <span class="px-2 py-0.5 rounded text-xs mono-data" style="color: var(--ss-text-muted);">Sim {{ simId }}</span>

        <!-- Sim status pill -->
        <span class="px-3 py-1 rounded-full text-xs font-semibold sim-status-pill"
          [class]="'sim-status-' + simStatus()">
          {{ simStatus() | uppercase }}
        </span>

        <div class="ml-auto flex items-center gap-2">
          @if (wsConnected()) {
            <span class="live-dot"></span>
            <span class="text-sm font-medium" style="color: var(--ss-success);">Live</span>
          } @else {
            <span class="text-sm" style="color: var(--ss-text-muted);">Disconnected</span>
          }
        </div>
      </header>

      <!-- KPI Grid -->
      <section class="kpi-grid mb-6">
        @if (simStatus() === 'failed') {
          <div class="kpi-error">
            <p class="font-medium mb-1">Simulation failed to start.</p>
            <p class="text-sm" style="color: var(--ss-text-muted);">The backend could not load the world model or agents. Try re-generating agents and starting a new simulation.</p>
          </div>
        } @else {
          @for (kpi of kpis(); track kpi.name) {
            <div class="glass-card kpi-card">
              <div class="kpi-name mono-data">{{ kpi.name }}</div>
              <div class="kpi-value mono-data">{{ kpi.value | number: '1.1-1' }}</div>
              <div class="kpi-trend" [class]="'trend-' + kpi.trend">
                {{ kpi.trend === 'up' ? '↑' : kpi.trend === 'down' ? '↓' : '→' }}
                <span class="trend-label">{{ kpi.trend }}</span>
              </div>
            </div>
          } @empty {
            <div class="kpi-waiting">
              <span class="text-sm" style="color: var(--ss-text-muted);">
                Waiting for simulation data… ({{ simStatus() }})
              </span>
            </div>
          }
        }
      </section>

      <!-- Tick Progress -->
      <section class="mb-5">
        @if (lastTick(); as tick) {
          <div class="glass-card p-4">
            <div class="flex items-center gap-4 flex-wrap">
              <div class="flex items-center gap-2 mono-data font-bold" style="color: var(--ss-cyan);">
                @if (simStatus() !== 'completed') {
                  <span class="live-dot" style="width:6px;height:6px;"></span>
                }
                Tick {{ tick.tick_number }} / {{ maxTicks() }}
              </div>

              <!-- Gradient progress bar -->
              <div class="flex-1" style="min-width: 160px;">
                <div style="height: 8px; border-radius: 999px; background: rgba(255,255,255,0.08); overflow: hidden;">
                  <div style="height: 100%; border-radius: 999px; background: linear-gradient(90deg, #06b6d4, #3b82f6); box-shadow: 0 0 10px rgba(6,182,212,0.5); transition: width 0.7s ease;"
                    [style.width.%]="(tick.tick_number / (maxTicks() || 1)) * 100">
                  </div>
                </div>
              </div>

              <div class="flex gap-3 text-xs mono-data" style="color: var(--ss-text-muted);">
                <span>{{ tick.active_agent_ids?.length ?? 0 }} agents</span>
                <span>{{ tick.events?.length ?? 0 }} events</span>
                <span>{{ tick.duration_ms ?? 0 }}ms</span>
              </div>
            </div>
          </div>
        } @else {
          <div class="glass-card p-4 flex items-center gap-3">
            <div class="w-4 h-4 rounded-full border-2 border-transparent animate-spin"
              style="border-top-color: var(--ss-cyan);"></div>
            <span class="text-sm" style="color: var(--ss-text-muted);">
              @if (simStatus() === 'pending') {
                Preparing agents... simulation will start shortly
              } @else if (simStatus() === 'running') {
                Running — waiting for first tick data...
              } @else {
                Waiting for first tick...
              }
            </span>
          </div>
        }
      </section>

      <!-- Nav links -->
      <div class="flex gap-2 mb-6 flex-wrap">
        <a class="px-4 py-1.5 rounded-lg text-sm font-medium no-underline transition-all duration-200"
          style="background: var(--ss-cyan-dim); color: var(--ss-cyan); border: 1px solid rgba(6,182,212,0.2);"
          [routerLink]="['/simulations', simId, 'report']">View Report</a>
        <a class="px-4 py-1.5 rounded-lg text-sm font-medium no-underline transition-all duration-200"
          style="background: var(--ss-bg-card); color: var(--ss-text-secondary); border: 1px solid var(--ss-border);"
          [routerLink]="['/simulations', simId, 'intervene']">Interventions</a>
        <a class="px-4 py-1.5 rounded-lg text-sm font-medium no-underline transition-all duration-200"
          style="background: var(--ss-bg-card); color: var(--ss-text-secondary); border: 1px solid var(--ss-border);"
          [routerLink]="['/simulations', simId, 'chat']">Agent Chat</a>
      </div>

      <!-- Event Log -->
      <section class="glass-card">
        <div class="px-4 py-3 flex items-center gap-2" style="border-bottom: 1px solid var(--ss-border);">
          <span class="text-sm font-semibold" style="color: var(--ss-text-primary);">Recent Events</span>
          <span class="text-xs px-1.5 py-0.5 rounded mono-data"
            style="background: var(--ss-cyan-dim); color: var(--ss-cyan);">
            {{ recentEvents().length }}
          </span>
        </div>
        <ul class="event-log-list list-none p-0 m-0">
          @for (event of recentEvents(); track $index) {
            <li class="event-item mono-data">{{ event }}</li>
          } @empty {
            <li class="px-4 py-8 text-center text-sm" style="color: var(--ss-text-muted);">No events yet.</li>
          }
        </ul>
      </section>
    </div>
  `,
  styles: [`
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
      gap: 1rem;
    }
    .kpi-card {
      padding: 1.25rem;
      text-align: center;
    }
    .kpi-name {
      font-size: 0.75rem;
      color: var(--ss-text-muted);
      margin-bottom: 0.5rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .kpi-value {
      font-size: 2rem;
      font-weight: 700;
      color: var(--ss-text-primary);
      line-height: 1;
      margin-bottom: 0.5rem;
    }
    .kpi-trend {
      font-size: 0.9rem;
      font-weight: 600;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 4px;
    }
    .trend-label { font-size: 0.7rem; opacity: 0.8; }
    .trend-up { color: var(--ss-cyan); }
    .trend-down { color: var(--ss-error); }
    .trend-flat { color: var(--ss-text-muted); }

    .kpi-error {
      grid-column: 1 / -1;
      background: var(--ss-error-dim);
      border: 1px solid rgba(244,63,94,0.3);
      border-radius: 12px;
      padding: 1.5rem;
      color: var(--ss-error);
    }
    .kpi-waiting {
      grid-column: 1 / -1;
      padding: 2rem;
      text-align: center;
    }

    .sim-status-pill { }
    .sim-status-pending { background: var(--ss-warning-dim); color: var(--ss-warning); }
    .sim-status-running {
      background: var(--ss-cyan-dim);
      color: var(--ss-cyan);
      animation: pulse-dot 2s ease-in-out infinite;
    }
    .sim-status-completed { background: var(--ss-success-dim); color: var(--ss-success); }
    .sim-status-failed { background: var(--ss-error-dim); color: var(--ss-error); }

    .event-log-list {
      max-height: 300px;
      overflow-y: auto;
    }
    .event-item {
      padding: 0.5rem 1rem;
      border-bottom: 1px solid var(--ss-border);
      font-size: 0.8rem;
      color: var(--ss-text-secondary);
      line-height: 1.5;
    }
    .event-item:last-child { border-bottom: none; }
    .event-item:hover { background: rgba(6,182,212,0.03); color: var(--ss-text-primary); }
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
