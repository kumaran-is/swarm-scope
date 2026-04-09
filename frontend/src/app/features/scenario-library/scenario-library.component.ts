import { Component, OnInit, OnDestroy, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { Subscription, interval } from 'rxjs';
import { switchMap } from 'rxjs/operators';
import { ScenarioService, Scenario } from '../../core/services/scenario.service';

@Component({
  selector: 'app-scenario-library',
  standalone: true,
  imports: [FormsModule],
  template: `
    <div class="animate-fade-up">
      <header class="flex justify-between items-center mb-8">
        <div>
          <h1 class="text-3xl font-bold tracking-tight" style="color: var(--ss-text-primary);">Scenario Library</h1>
          <p class="mt-1 text-sm" style="color: var(--ss-text-secondary);">Your simulation scenarios</p>
        </div>
        <button class="px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-200 cursor-pointer border-0"
          style="background: linear-gradient(135deg, var(--ss-cyan), var(--ss-blue)); color: #fff; box-shadow: var(--ss-glow-cyan);"
          (click)="create()">
          + New Scenario
        </button>
      </header>

      <div class="flex flex-wrap gap-3 mb-6">
        <input class="input flex-1 min-w-48 text-sm"
          style="background: var(--ss-bg-card); border: 1px solid var(--ss-border); color: var(--ss-text-primary); border-radius: 8px; padding: 0.5rem 0.875rem;"
          [(ngModel)]="searchQuery" placeholder="Search by name…"
          (ngModelChange)="applyFilters()" />
        <select class="select text-sm"
          style="background: var(--ss-bg-card); border: 1px solid var(--ss-border); color: var(--ss-text-primary); border-radius: 8px; padding: 0.5rem 0.875rem;"
          [(ngModel)]="filterDomain" (ngModelChange)="applyFilters()">
          <option value="">All Domains</option>
          <option value="geopolitics">Geopolitics</option>
          <option value="economics">Economics</option>
          <option value="social">Social</option>
          <option value="general">General</option>
        </select>
        <select class="select text-sm"
          style="background: var(--ss-bg-card); border: 1px solid var(--ss-border); color: var(--ss-text-primary); border-radius: 8px; padding: 0.5rem 0.875rem;"
          [(ngModel)]="filterStatus" (ngModelChange)="applyFilters()">
          <option value="">All Statuses</option>
          <option value="draft">Draft</option>
          <option value="world_compiled">Compiled</option>
          <option value="agents_generated">Agents Ready</option>
          <option value="ready">Ready</option>
        </select>
        <select class="select text-sm"
          style="background: var(--ss-bg-card); border: 1px solid var(--ss-border); color: var(--ss-text-primary); border-radius: 8px; padding: 0.5rem 0.875rem;"
          [(ngModel)]="sortBy" (ngModelChange)="applyFilters()">
          <option value="date">Sort by Date</option>
          <option value="name">Sort by Name</option>
          <option value="status">Sort by Status</option>
        </select>
      </div>

      @if (loading()) {
        <div class="flex flex-col justify-center items-center py-24 gap-4">
          <div class="w-10 h-10 rounded-full border-2 border-transparent animate-spin"
            style="border-top-color: var(--ss-cyan); border-right-color: var(--ss-blue);"></div>
          <p class="text-sm" style="color: var(--ss-text-muted);">Loading scenarios...</p>
        </div>
      } @else if (filtered().length === 0) {
        <div class="flex flex-col items-center justify-center py-24 gap-4">
          <div class="w-16 h-16 rounded-full flex items-center justify-center text-3xl"
            style="background: var(--ss-cyan-dim); border: 1px solid rgba(6,182,212,0.2);">
            &#128196;
          </div>
          <div class="text-center">
            <p class="text-lg font-medium mb-1" style="color: var(--ss-text-primary);">No scenarios yet</p>
            <p class="text-sm mb-6" style="color: var(--ss-text-muted);">Create your first simulation scenario to get started.</p>
          </div>
          <button class="px-5 py-2 rounded-lg text-sm font-semibold border-0 cursor-pointer transition-all duration-200"
            style="background: linear-gradient(135deg, var(--ss-cyan), var(--ss-blue)); color: #fff;"
            (click)="create()">
            + New Scenario
          </button>
        </div>
      } @else {
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          @for (s of filtered(); track s.id) {
            <div class="scenario-card glass-card glass-card--glow cursor-pointer"
              (click)="navigate(s)">
              <div class="p-5 flex flex-col gap-3">

                <div class="flex gap-2 flex-wrap items-center">
                  <span class="px-2 py-0.5 rounded text-xs font-medium"
                    style="background: var(--ss-blue-dim); color: var(--ss-blue); border: 1px solid rgba(59,130,246,0.2);">
                    {{ s.domain }}
                  </span>
                  <span class="status-pill px-2 py-0.5 rounded-full text-xs font-semibold"
                    [class]="'status-' + s.status">
                    {{ statusLabel(s.status) }}
                  </span>
                </div>

                <h2 class="text-base font-semibold leading-snug" style="color: var(--ss-text-primary);">{{ s.name }}</h2>

                @if (s.description) {
                  <p class="text-sm line-clamp-2" style="color: var(--ss-text-secondary);">{{ s.description }}</p>
                }

                <!-- Pipeline step indicator -->
                <div class="flex items-center gap-0">
                  @for (step of pipeline; track step.key; let last = $last) {
                    <div class="flex items-center gap-0">
                      <div class="flex flex-col items-center gap-1" [title]="step.label">
                        <div class="w-3 h-3 rounded-full flex items-center justify-center"
                          [style]="isStepDone(s.status, step.key)
                            ? 'background: var(--ss-success); box-shadow: 0 0 6px rgba(16,185,129,0.5);'
                            : 'background: var(--ss-border); border: 1px solid var(--ss-border-bright);'">
                        </div>
                        <span class="text-xs" style="font-size: 10px;"
                          [style.color]="isStepDone(s.status, step.key) ? 'var(--ss-success)' : 'var(--ss-text-muted)'">
                          {{ step.label }}
                        </span>
                      </div>
                      @if (!last) {
                        <div class="h-px w-6 mx-1 mb-4"
                          [style]="isStepDone(s.status, step.key) ? 'background: var(--ss-success);' : 'background: var(--ss-border);'">
                        </div>
                      }
                    </div>
                  }
                </div>

                <div class="flex justify-end gap-2 mt-1 pt-2" style="border-top: 1px solid var(--ss-border);" (click)="$event.stopPropagation()">
                  <button class="px-3 py-1 rounded text-xs font-medium border-0 cursor-pointer transition-colors duration-150"
                    style="background: transparent; color: var(--ss-text-secondary);"
                    onmouseover="this.style.color='var(--ss-text-primary)'; this.style.background='var(--ss-border)';"
                    onmouseout="this.style.color='var(--ss-text-secondary)'; this.style.background='transparent';"
                    (click)="clone(s)">Clone</button>
                  <button class="px-3 py-1 rounded text-xs font-medium border-0 cursor-pointer transition-colors duration-150"
                    style="background: transparent; color: var(--ss-error);"
                    onmouseover="this.style.background='var(--ss-error-dim)';"
                    onmouseout="this.style.background='transparent';"
                    (click)="confirmDelete(s)">Delete</button>
                </div>
              </div>
            </div>
          }
        </div>
      }

      @if (confirmDeleteId()) {
        <div class="modal modal-open">
          <div class="modal-backdrop" (click)="confirmDeleteId.set(null)"></div>
          <div class="modal-box" style="background: var(--ss-bg-card); border: 1px solid var(--ss-border);">
            <h3 class="font-bold text-lg" style="color: var(--ss-text-primary);">Delete Scenario?</h3>
            <p class="py-4 text-sm" style="color: var(--ss-text-secondary);">
              This will permanently delete the scenario and all associated data.
            </p>
            <div class="modal-action">
              <button class="btn btn-ghost btn-sm" (click)="confirmDeleteId.set(null)">Cancel</button>
              <button class="btn btn-sm border-0 text-white cursor-pointer"
                style="background: var(--ss-error);"
                (click)="deleteScenario()">Delete</button>
            </div>
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    .scenario-card {
      transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
    }
    .scenario-card:hover {
      transform: translateY(-3px);
    }
    .status-pill { display: inline-flex; align-items: center; gap: 4px; }
    .status-draft { background: rgba(71,85,105,0.3); color: #94a3b8; }
    .status-compiling, .status-generating_agents {
      background: rgba(245,158,11,0.15);
      color: #f59e0b;
      animation: pulse-dot 1.5s ease-in-out infinite;
    }
    .status-world_compiled { background: rgba(59,130,246,0.15); color: #3b82f6; }
    .status-agents_generated { background: rgba(139,92,246,0.15); color: #8b5cf6; }
    .status-ready { background: rgba(16,185,129,0.15); color: #10b981; }
  `],
})
export class ScenarioLibraryComponent implements OnInit, OnDestroy {
  private svc = inject(ScenarioService);
  private router = inject(Router);

  scenarios = signal<Scenario[]>([]);
  loading = signal(false);
  confirmDeleteId = signal<string | null>(null);
  private pollSub?: Subscription;

  searchQuery = '';
  filterDomain = '';
  filterStatus = '';
  sortBy: 'date' | 'name' | 'status' = 'date';

  filtered = signal<Scenario[]>([]);

  pipeline = [
    { key: 'draft', label: 'Draft' },
    { key: 'world_compiled', label: 'Compiled' },
    { key: 'agents_generated', label: 'Agents' },
    { key: 'ready', label: 'Ready' },
  ];

  private statusOrder: Record<string, number> = {
    draft: 0,
    compiling: 1,
    world_compiled: 2,
    generating_agents: 3,
    agents_generated: 4,
    ready: 5,
  };

  ngOnInit(): void {
    this.load();
    // Poll every 5s to pick up status changes (compiling → compiled, generating → ready)
    this.pollSub = interval(5000).pipe(
      switchMap(() => this.svc.list()),
    ).subscribe({
      next: (s) => { this.scenarios.set(s); this.applyFilters(); },
      error: () => {},
    });
  }

  ngOnDestroy(): void {
    this.pollSub?.unsubscribe();
  }

  load(): void {
    this.loading.set(true);
    this.svc.list().subscribe({
      next: (s) => {
        this.scenarios.set(s);
        this.loading.set(false);
        this.applyFilters();
      },
      error: (err: Error) => {
        this.loading.set(false);
        // Error surfaced via toast — no silent swallow
        throw err;
      },
    });
  }

  applyFilters(): void {
    let list = [...this.scenarios()];
    if (this.searchQuery.trim()) {
      const q = this.searchQuery.toLowerCase();
      list = list.filter((s) => s.name.toLowerCase().includes(q));
    }
    if (this.filterDomain) {
      list = list.filter((s) => s.domain === this.filterDomain);
    }
    if (this.filterStatus) {
      list = list.filter((s) => s.status === this.filterStatus);
    }
    if (this.sortBy === 'name') {
      list.sort((a, b) => a.name.localeCompare(b.name));
    } else if (this.sortBy === 'status') {
      list.sort((a, b) => (this.statusOrder[b.status] ?? 0) - (this.statusOrder[a.status] ?? 0));
    } else {
      list.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());
    }
    this.filtered.set(list);
  }

  statusLabel(status: string): string {
    const labels: Record<string, string> = {
      draft: 'Draft',
      compiling: 'Compiling\u2026',
      world_compiled: 'Compiled',
      generating_agents: 'Generating\u2026',
      agents_generated: 'Agents Ready',
      ready: 'Ready',
    };
    return labels[status] ?? status;
  }

  statusBadgeClass(status: string): string {
    const classes: Record<string, string> = {
      draft: 'badge-ghost',
      compiling: 'badge-warning',
      world_compiled: 'badge-info',
      generating_agents: 'badge-warning',
      agents_generated: 'badge-secondary',
      ready: 'badge-success',
    };
    return classes[status] ?? 'badge-ghost';
  }

  isStepDone(status: string, stepKey: string): boolean {
    const current = this.statusOrder[status] ?? 0;
    const step = this.statusOrder[stepKey] ?? 0;
    return current >= step;
  }

  navigate(s: Scenario): void {
    const order = this.statusOrder[s.status] ?? 0;
    if (order >= 4) {
      this.router.navigate(['/simulations', s.id, 'control']);
    } else if (order >= 2) {
      this.router.navigate(['/scenarios', s.id, 'world']);
    } else {
      this.router.navigate(['/scenarios/new']);
    }
  }

  create(): void {
    this.router.navigate(['/scenarios/new']);
  }

  clone(s: Scenario): void {
    const fd = new FormData();
    fd.append('name', `${s.name} (Copy)`);
    if (s.description) fd.append('description', s.description);
    fd.append('domain', s.domain);
    fd.append('config', JSON.stringify(s.config));
    this.svc.create(fd).subscribe({
      next: () => this.load(),
      error: (err: Error) => { throw err; },
    });
  }

  confirmDelete(s: Scenario): void {
    this.confirmDeleteId.set(s.id);
  }

  deleteScenario(): void {
    const id = this.confirmDeleteId();
    if (!id) return;
    this.svc.delete(id).subscribe({
      next: () => {
        this.confirmDeleteId.set(null);
        this.load();
      },
      error: (err: Error) => { throw err; },
    });
  }
}
