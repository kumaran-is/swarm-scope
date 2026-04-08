import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { InterventionService, Intervention } from '../../core/services/intervention.service';

type InterventionType = 'inject_event' | 'modify_kpi' | 'agent_directive';

interface InterventionForm {
  type: InterventionType;
  description: string;
  payload: string;
  target_tick: number | null;
}

@Component({
  selector: 'app-intervention-console',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="console">
      <div class="breadcrumbs text-sm mb-4">
        <ul>
          <li><a [routerLink]="['/scenarios']">Scenarios</a></li>
          <li><a [routerLink]="['/simulations', simId, 'dashboard']">Live Dashboard</a></li>
          <li>Interventions</li>
        </ul>
      </div>
      <h1>Intervention Console</h1>
      <p class="subtitle">Sim {{ simId }}</p>

      <div class="type-cards">
        @for (t of types; track t.value) {
          <button class="type-card" [class.active]="form.type === t.value" (click)="form.type = t.value">
            <span class="type-icon">{{ t.icon }}</span>
            <span class="type-label">{{ t.label }}</span>
            <span class="type-desc">{{ t.desc }}</span>
          </button>
        }
      </div>

      <div class="form-section">
        <label>Description
          <input [(ngModel)]="form.description" placeholder="What this intervention does..." />
        </label>
        <label>Payload (JSON)
          <textarea [(ngModel)]="form.payload" rows="4" placeholder='{ "key": "value" }'></textarea>
        </label>
        <label>Target Tick (optional)
          <input type="number" [(ngModel)]="form.target_tick" placeholder="Apply at tick #" />
        </label>
        @if (error()) {
          <p class="error">{{ error() }}</p>
        }
        <button class="submit-btn" (click)="submit()" [disabled]="submitting()">
          {{ submitting() ? 'Submitting…' : 'Apply Intervention' }}
        </button>
      </div>

      <section class="history">
        <h2>Applied Interventions</h2>
        @for (iv of interventions(); track iv.id) {
          <div class="iv-row">
            <span class="iv-type">{{ iv.type }}</span>
            <span class="iv-desc">{{ iv.description }}</span>
            <span class="iv-status" [class]="iv.status">{{ iv.status }}</span>
            @if (iv.status === 'pending') {
              <button class="cancel-btn" (click)="cancel(iv.id)">Cancel</button>
            }
          </div>
        } @empty {
          <p class="empty-state">No interventions yet.</p>
        }
      </section>
    </div>
  `,
  styles: [`
    .console { padding: 1.5rem; max-width: 800px; }
    h1 { margin-bottom: 0.25rem; }
    .subtitle { color: #888; margin-bottom: 1.5rem; }
    .type-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem; margin-bottom: 1.5rem; }
    .type-card { background: #1e1e2e; border: 2px solid transparent; border-radius: 8px; padding: 1rem; cursor: pointer; display: flex; flex-direction: column; gap: 0.25rem; text-align: left; }
    .type-card.active { border-color: #7c3aed; }
    .type-icon { font-size: 1.5rem; }
    .type-label { font-weight: 600; }
    .type-desc { font-size: 0.8rem; color: #888; }
    .form-section { display: flex; flex-direction: column; gap: 0.75rem; margin-bottom: 2rem; }
    label { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.9rem; }
    input, textarea { background: #1e1e2e; border: 1px solid #444; border-radius: 6px; padding: 0.5rem 0.75rem; color: inherit; font-family: monospace; }
    .submit-btn { background: #7c3aed; color: #fff; border: none; border-radius: 6px; padding: 0.75rem; cursor: pointer; font-size: 1rem; }
    .submit-btn:disabled { opacity: 0.5; cursor: not-allowed; }
    .error { color: #f44336; font-size: 0.9rem; }
    .history h2 { font-size: 1rem; margin-bottom: 0.5rem; }
    .iv-row { display: flex; align-items: center; gap: 1rem; padding: 0.5rem 0; border-bottom: 1px solid #2a2a3e; font-size: 0.9rem; }
    .iv-type { font-weight: 600; font-size: 0.8rem; background: #2a2a3e; padding: 0.2rem 0.5rem; border-radius: 4px; }
    .iv-desc { flex: 1; color: #ccc; }
    .iv-status.pending { color: #ff9800; }
    .iv-status.applied { color: #4caf50; }
    .iv-status.cancelled { color: #888; }
    .cancel-btn { background: none; border: 1px solid #f44336; color: #f44336; border-radius: 4px; padding: 0.2rem 0.5rem; cursor: pointer; font-size: 0.8rem; }
    .empty-state { color: #888; font-style: italic; }
  `],
})
export class InterventionConsoleComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private ivService = inject(InterventionService);

  simId = '';
  interventions = signal<Intervention[]>([]);
  submitting = signal(false);
  error = signal('');

  types = [
    { value: 'inject_event' as InterventionType, icon: '⚡', label: 'Inject Event', desc: 'Force a narrative event into the simulation' },
    { value: 'modify_kpi' as InterventionType, icon: '📊', label: 'Modify KPI', desc: 'Override a KPI value directly' },
    { value: 'agent_directive' as InterventionType, icon: '🤖', label: 'Agent Directive', desc: 'Send a command to a specific agent' },
  ];

  form: InterventionForm = {
    type: 'inject_event',
    description: '',
    payload: '{}',
    target_tick: null,
  };

  ngOnInit(): void {
    this.simId = this.route.snapshot.paramMap.get('id') ?? '';
    this.loadInterventions();
  }

  loadInterventions(): void {
    this.ivService.list(this.simId).subscribe({
      next: (ivs) => this.interventions.set(ivs),
      error: (err) => console.error('Failed to load interventions', err),
    });
  }

  submit(): void {
    this.error.set('');
    let payload: Record<string, unknown>;
    try {
      payload = JSON.parse(this.form.payload) as Record<string, unknown>;
    } catch {
      this.error.set('Payload must be valid JSON.');
      return;
    }

    this.submitting.set(true);
    this.ivService.create(this.simId, {
      type: this.form.type,
      description: this.form.description,
      payload,
      target_tick: this.form.target_tick ?? undefined,
    }).subscribe({
      next: () => {
        this.submitting.set(false);
        this.form = { type: this.form.type, description: '', payload: '{}', target_tick: null };
        this.loadInterventions();
      },
      error: (err: Error) => {
        this.submitting.set(false);
        this.error.set(err.message);
      },
    });
  }

  cancel(ivId: string): void {
    this.ivService.cancel(this.simId, ivId).subscribe({
      next: () => this.loadInterventions(),
      error: (err) => console.error('Cancel failed', err),
    });
  }
}
