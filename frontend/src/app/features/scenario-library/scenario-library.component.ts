import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ScenarioService, Scenario } from '../../core/services/scenario.service';

@Component({
  selector: 'app-scenario-library',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="library">
      <header class="library-header">
        <h1>Scenario Library</h1>
        <button class="create-btn" (click)="create()">+ New Scenario</button>
      </header>

      <div class="filters">
        <input [(ngModel)]="searchQuery" placeholder="Search by name…" (ngModelChange)="applyFilters()" />
        <select [(ngModel)]="filterDomain" (ngModelChange)="applyFilters()">
          <option value="">All Domains</option>
          <option value="geopolitics">Geopolitics</option>
          <option value="economics">Economics</option>
          <option value="social">Social</option>
          <option value="general">General</option>
        </select>
        <select [(ngModel)]="filterStatus" (ngModelChange)="applyFilters()">
          <option value="">All Statuses</option>
          <option value="draft">Draft</option>
          <option value="world_compiled">Compiled</option>
          <option value="agents_generated">Agents Ready</option>
          <option value="ready">Ready</option>
        </select>
        <select [(ngModel)]="sortBy" (ngModelChange)="applyFilters()">
          <option value="date">Sort by Date</option>
          <option value="name">Sort by Name</option>
          <option value="status">Sort by Status</option>
        </select>
      </div>

      @if (loading()) {
        <p class="loading">Loading scenarios…</p>
      } @else if (filtered().length === 0) {
        <div class="empty-state">
          <p>No scenarios yet. Create your first one.</p>
          <button class="create-btn" (click)="create()">+ New Scenario</button>
        </div>
      } @else {
        <div class="card-grid">
          @for (s of filtered(); track s.id) {
            <div class="scenario-card" (click)="navigate(s)">
              <div class="card-top">
                <span class="domain-badge">{{ s.domain }}</span>
                <span class="status-badge" [class]="s.status">{{ statusLabel(s.status) }}</span>
              </div>
              <h2 class="card-name">{{ s.name }}</h2>
              @if (s.description) {
                <p class="card-desc">{{ s.description }}</p>
              }
              <div class="status-pipeline">
                @for (step of pipeline; track step.key) {
                  <div class="pipeline-step" [class.done]="isStepDone(s.status, step.key)" [title]="step.label">
                    <span class="step-dot"></span>
                    <span class="step-label">{{ step.label }}</span>
                  </div>
                }
              </div>
              <div class="card-actions" (click)="$event.stopPropagation()">
                <button class="action-btn" (click)="clone(s)">Clone</button>
                <button class="action-btn danger" (click)="confirmDelete(s)">Delete</button>
              </div>
            </div>
          }
        </div>
      }

      @if (confirmDeleteId()) {
        <div class="modal-overlay" (click)="confirmDeleteId.set(null)">
          <div class="modal" (click)="$event.stopPropagation()">
            <h3>Delete Scenario?</h3>
            <p>This will permanently delete the scenario and all associated data.</p>
            <div class="modal-actions">
              <button (click)="confirmDeleteId.set(null)">Cancel</button>
              <button class="danger" (click)="deleteScenario()">Delete</button>
            </div>
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    .library { padding: 1.5rem; }
    .library-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
    .create-btn { background: #7c3aed; color: #fff; border: none; border-radius: 6px; padding: 0.5rem 1rem; cursor: pointer; }
    .filters { display: flex; gap: 0.75rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
    .filters input, .filters select { background: #1e1e2e; border: 1px solid #444; border-radius: 6px; padding: 0.4rem 0.75rem; color: inherit; }
    .filters input { flex: 1; min-width: 180px; }
    .card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem; }
    .scenario-card { background: #1e1e2e; border-radius: 10px; padding: 1.25rem; cursor: pointer; border: 2px solid transparent; transition: border-color 0.2s; }
    .scenario-card:hover { border-color: #7c3aed; }
    .card-top { display: flex; gap: 0.5rem; margin-bottom: 0.75rem; }
    .domain-badge { font-size: 0.75rem; background: #2a2a3e; padding: 0.2rem 0.5rem; border-radius: 4px; }
    .status-badge { font-size: 0.75rem; padding: 0.2rem 0.5rem; border-radius: 4px; }
    .status-badge.draft { background: #444; }
    .status-badge.world_compiled { background: #1565c0; }
    .status-badge.agents_generated { background: #6a1b9a; color: #fff; }
    .status-badge.ready { background: #2e7d32; color: #fff; }
    .card-name { font-size: 1rem; font-weight: 700; margin-bottom: 0.4rem; }
    .card-desc { font-size: 0.85rem; color: #888; margin-bottom: 0.75rem; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
    .status-pipeline { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 0.75rem; }
    .pipeline-step { display: flex; align-items: center; gap: 0.25rem; }
    .step-dot { width: 8px; height: 8px; border-radius: 50%; background: #444; }
    .pipeline-step.done .step-dot { background: #4caf50; }
    .step-label { font-size: 0.7rem; color: #888; }
    .pipeline-step.done .step-label { color: #4caf50; }
    .card-actions { display: flex; gap: 0.5rem; margin-top: 0.5rem; }
    .action-btn { background: none; border: 1px solid #444; border-radius: 4px; padding: 0.25rem 0.6rem; cursor: pointer; font-size: 0.8rem; color: #ccc; }
    .action-btn.danger { border-color: #f44336; color: #f44336; }
    .loading, .empty-state { color: #888; text-align: center; padding: 3rem; }
    .modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.7); display: flex; align-items: center; justify-content: center; z-index: 100; }
    .modal { background: #1e1e2e; border-radius: 10px; padding: 2rem; max-width: 400px; }
    .modal h3 { margin-bottom: 0.75rem; }
    .modal p { color: #888; margin-bottom: 1.5rem; }
    .modal-actions { display: flex; gap: 1rem; justify-content: flex-end; }
    .modal-actions button { padding: 0.5rem 1rem; border-radius: 6px; cursor: pointer; border: none; }
    .modal-actions button:first-child { background: #2a2a3e; color: #fff; }
    .modal-actions button.danger { background: #f44336; color: #fff; }
  `],
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
      error: (err) => {
        console.error('Failed to load scenarios', err);
        this.loading.set(false);
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
      compiling: 'Compiling…',
      world_compiled: 'Compiled',
      generating_agents: 'Generating…',
      agents_generated: 'Agents Ready',
      ready: 'Ready',
    };
    return labels[status] ?? status;
  }

  isStepDone(status: string, stepKey: string): boolean {
    const current = this.statusOrder[status] ?? 0;
    const step = this.statusOrder[stepKey] ?? 0;
    return current >= step;
  }

  navigate(s: Scenario): void {
    const order = this.statusOrder[s.status] ?? 0;
    if (order >= 4) {
      this.router.navigate(['/scenarios', s.id, 'world']);
    } else if (order >= 2) {
      this.router.navigate(['/scenarios', s.id, 'world']);
    } else {
      this.router.navigate(['/scenarios']);
    }
  }

  create(): void {
    this.router.navigate(['/scenarios']);
  }

  clone(s: Scenario): void {
    const fd = new FormData();
    fd.append('name', `${s.name} (Copy)`);
    if (s.description) fd.append('description', s.description);
    fd.append('domain', s.domain);
    fd.append('config', JSON.stringify(s.config));
    this.svc.create(fd).subscribe({
      next: () => this.load(),
      error: (err) => console.error('Clone failed', err),
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
      error: (err) => console.error('Delete failed', err),
    });
  }
}
