import { Component, OnInit, OnDestroy, inject, signal } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { interval, Subscription, switchMap, take, catchError, EMPTY } from 'rxjs';
import { ScenarioService } from '../../core/services/scenario.service';

const POLL_INTERVAL_MS = 2000;
const MAX_RETRIES = 30;

@Component({
  selector: 'app-world-editor',
  standalone: true,
  imports: [FormsModule],
  template: `
    <div class="world-editor">
      <h1>World Model Editor</h1>
      @if (loading()) {
        <div class="flex flex-col items-center gap-3 py-12">
          <span class="loading loading-spinner loading-lg text-primary"></span>
          <p class="text-base-content/60">Extracting world model via Gemini&hellip; ({{ pollAttempt() }}/{{ maxRetries }})</p>
        </div>
      }
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
        <div class="flex gap-3 mt-6">
          <button class="btn btn-outline btn-sm" (click)="save()">Save Changes</button>
          <button class="btn btn-primary" (click)="generateAgents()" [disabled]="generating()">
            @if (generating()) {
              <span class="loading loading-spinner loading-sm"></span>
              Generating Agents...
            } @else {
              Generate Agents
            }
          </button>
        </div>
      }
      @if (error()) { <p class="error">{{ error() }}</p> }
    </div>
  `,
})
export class WorldEditorComponent implements OnInit, OnDestroy {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private svc = inject(ScenarioService);

  readonly maxRetries = MAX_RETRIES;

  scenarioId = '';
  world = signal<any>(null);
  loading = signal(true);
  generating = signal(false);
  error = signal('');
  pollAttempt = signal(0);

  private pollSub: Subscription | null = null;

  ngOnInit(): void {
    this.scenarioId = this.route.snapshot.paramMap.get('id') ?? '';
    this.startPolling();
  }

  ngOnDestroy(): void {
    this.pollSub?.unsubscribe();
  }

  private startPolling(): void {
    this.pollSub = interval(POLL_INTERVAL_MS)
      .pipe(
        take(MAX_RETRIES),
        switchMap(() => {
          this.pollAttempt.update(n => n + 1);
          return this.svc.getWorldModel(this.scenarioId).pipe(
            catchError(() => EMPTY), // swallow per-request errors; keep polling
          );
        }),
      )
      .subscribe({
        next: (w) => {
          if (w) {
            this.world.set(w);
            this.loading.set(false);
            this.pollSub?.unsubscribe();
          }
        },
        complete: () => {
          // All retries exhausted without a successful response
          if (!this.world()) {
            this.error.set('World model not found after waiting. The extraction may have failed — please try recompiling.');
            this.loading.set(false);
          }
        },
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
