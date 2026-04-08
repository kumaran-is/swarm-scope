import { Component, OnInit, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ScenarioService, Scenario } from '../../core/services/scenario.service';

@Component({
  selector: 'app-scenario-library',
  standalone: true,
  imports: [FormsModule],
  template: `
    <div>
      <header class="flex justify-between items-center mb-6">
        <div>
          <h1 class="text-3xl font-bold">Scenario Library</h1>
          <p class="text-base-content/60 mt-1">Your simulation scenarios</p>
        </div>
        <button class="btn btn-primary" (click)="create()">+ New Scenario</button>
      </header>

      <div class="flex flex-wrap gap-3 mb-6">
        <input class="input input-bordered flex-1 min-w-48"
          [(ngModel)]="searchQuery" placeholder="Search by name&hellip;"
          (ngModelChange)="applyFilters()" />
        <select class="select select-bordered" [(ngModel)]="filterDomain" (ngModelChange)="applyFilters()">
          <option value="">All Domains</option>
          <option value="geopolitics">Geopolitics</option>
          <option value="economics">Economics</option>
          <option value="social">Social</option>
          <option value="general">General</option>
        </select>
        <select class="select select-bordered" [(ngModel)]="filterStatus" (ngModelChange)="applyFilters()">
          <option value="">All Statuses</option>
          <option value="draft">Draft</option>
          <option value="world_compiled">Compiled</option>
          <option value="agents_generated">Agents Ready</option>
          <option value="ready">Ready</option>
        </select>
        <select class="select select-bordered" [(ngModel)]="sortBy" (ngModelChange)="applyFilters()">
          <option value="date">Sort by Date</option>
          <option value="name">Sort by Name</option>
          <option value="status">Sort by Status</option>
        </select>
      </div>

      @if (loading()) {
        <div class="flex justify-center items-center py-16">
          <span class="loading loading-spinner loading-lg text-primary"></span>
        </div>
      } @else if (filtered().length === 0) {
        <div class="text-center py-16 text-base-content/40">
          <p class="text-4xl mb-4">&#128196;</p>
          <p class="text-lg font-medium mb-2">No scenarios yet</p>
          <p class="text-sm mb-6">Create your first simulation scenario to get started.</p>
          <button class="btn btn-primary" (click)="create()">+ New Scenario</button>
        </div>
      } @else {
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          @for (s of filtered(); track s.id) {
            <div class="card bg-base-200 border border-base-300 hover:border-primary cursor-pointer transition-all hover:shadow-lg"
              (click)="navigate(s)">
              <div class="card-body gap-3">

                <div class="flex gap-2 flex-wrap">
                  <span class="badge badge-ghost badge-sm">{{ s.domain }}</span>
                  <span class="badge badge-sm" [class]="statusBadgeClass(s.status)">
                    {{ statusLabel(s.status) }}
                  </span>
                </div>

                <h2 class="card-title text-base">{{ s.name }}</h2>

                @if (s.description) {
                  <p class="text-base-content/60 text-sm line-clamp-2">{{ s.description }}</p>
                }

                <div class="flex gap-2 flex-wrap">
                  @for (step of pipeline; track step.key) {
                    <div class="flex items-center gap-1" [title]="step.label">
                      <span class="w-2 h-2 rounded-full"
                        [class]="isStepDone(s.status, step.key) ? 'bg-success' : 'bg-base-300'">
                      </span>
                      <span class="text-xs"
                        [class]="isStepDone(s.status, step.key) ? 'text-success' : 'text-base-content/30'">
                        {{ step.label }}
                      </span>
                    </div>
                  }
                </div>

                <div class="card-actions justify-end mt-1" (click)="$event.stopPropagation()">
                  <button class="btn btn-ghost btn-xs" (click)="clone(s)">Clone</button>
                  <button class="btn btn-ghost btn-xs text-error" (click)="confirmDelete(s)">Delete</button>
                </div>

              </div>
            </div>
          }
        </div>
      }

      @if (confirmDeleteId()) {
        <div class="modal modal-open">
          <div class="modal-backdrop" (click)="confirmDeleteId.set(null)"></div>
          <div class="modal-box">
            <h3 class="font-bold text-lg">Delete Scenario?</h3>
            <p class="py-4 text-base-content/60">
              This will permanently delete the scenario and all associated data.
            </p>
            <div class="modal-action">
              <button class="btn btn-ghost" (click)="confirmDeleteId.set(null)">Cancel</button>
              <button class="btn btn-error" (click)="deleteScenario()">Delete</button>
            </div>
          </div>
        </div>
      }
    </div>
  `,
})
export class ScenarioLibraryComponent implements OnInit {
  private svc = inject(ScenarioService);
  private router = inject(Router);

  scenarios = signal<Scenario[]>([]);
  loading = signal(false);
  confirmDeleteId = signal<string | null>(null);

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
    if (order >= 2) {
      this.router.navigate(['/scenarios', s.id, 'world']);
    } else {
      this.router.navigate(['/scenarios']);
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
