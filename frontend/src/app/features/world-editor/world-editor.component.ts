import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ScenarioService } from '../../core/services/scenario.service';

@Component({
  selector: 'app-world-editor',
  standalone: true,
  imports: [FormsModule],
  template: `
    <div class="world-editor">
      <h1>World Model Editor</h1>
      @if (loading()) { <p>Loading world model...</p> }
      @if (world()) {
        <section>
          <h2>Summary</h2>
          <textarea [(ngModel)]="world()!.summary" rows="4" style="width:100%"></textarea>
        </section>
        <section>
          <h2>KPIs ({{ world()!.kpis.length }})</h2>
          @for (kpi of world()!.kpis; track kpi.name) {
            <div class="kpi-row">
              <strong>{{ kpi.name }}</strong> — {{ kpi.description }} ({{ kpi.unit }}, init={{ kpi.initial_value }}, target={{ kpi.target }})
            </div>
          }
        </section>
        <section>
          <h2>Entities ({{ world()!.entities.length }})</h2>
          @for (e of world()!.entities; track e.name) {
            <div>{{ e.name }} [{{ e.type }}] — {{ e.description }}</div>
          }
        </section>
        <section>
          <h2>Tensions ({{ world()!.tensions.length }})</h2>
          @for (t of world()!.tensions; track t.description) {
            <div>{{ t.between.join(' vs ') }} — Intensity {{ t.intensity }}/10: {{ t.description }}</div>
          }
        </section>
        <div class="actions">
          <button (click)="save()">Save Changes</button>
          <button (click)="generateAgents()" [disabled]="generating()">
            {{ generating() ? 'Generating Agents...' : 'Generate Agents' }}
          </button>
        </div>
      }
      @if (error()) { <p class="error">{{ error() }}</p> }
    </div>
  `,
})
export class WorldEditorComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private svc = inject(ScenarioService);

  scenarioId = '';
  world = signal<any>(null);
  loading = signal(true);
  generating = signal(false);
  error = signal('');

  ngOnInit(): void {
    this.scenarioId = this.route.snapshot.paramMap.get('id') ?? '';
    this.svc.getWorldModel(this.scenarioId).subscribe({
      next: (w) => { this.world.set(w); this.loading.set(false); },
      error: (e) => { this.error.set(e.message); this.loading.set(false); },
    });
  }

  save(): void {
    this.svc.updateWorldModel(this.scenarioId, this.world()).subscribe({
      next: (w) => this.world.set(w),
      error: (e) => this.error.set(e.message),
    });
  }

  generateAgents(): void {
    this.generating.set(true);
    this.svc.generateAgents(this.scenarioId, 20).subscribe({
      next: () => this.router.navigate(['/simulations', this.scenarioId, 'control']),
      error: (e) => { this.error.set(e.message); this.generating.set(false); },
    });
  }
}
