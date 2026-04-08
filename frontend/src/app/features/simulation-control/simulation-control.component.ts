import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { CommonModule } from '@angular/common';
import { SimulationService, SimulationRun } from '../../core/services/simulation.service';

@Component({
  selector: 'app-simulation-control',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="sim-control">
      <h1>Simulation Control</h1>
      @if (run()) {
        <div class="status-bar">
          <span>Status: <strong>{{ run()!.status }}</strong></span>
          <span>Tick: {{ run()!.current_tick }} / {{ run()!.max_ticks }}</span>
        </div>
        <div class="controls">
          <button (click)="start()" [disabled]="run()!.status === 'running'">Start</button>
          <button (click)="pause()" [disabled]="run()!.status !== 'running'">Pause</button>
          <button (click)="resume()" [disabled]="run()!.status !== 'paused'">Resume</button>
          <button (click)="stop()">Stop</button>
        </div>
        <div class="nav-links">
          <a [routerLink]="['/simulations', run()!.id, 'dashboard']">Live Dashboard</a>
          <a [routerLink]="['/simulations', run()!.id, 'intervene']">Interventions</a>
          <a [routerLink]="['/simulations', run()!.id, 'chat']">Agent Chat</a>
          <a [routerLink]="['/simulations', run()!.id, 'report']">Report</a>
        </div>
      }
      @if (!run() && !loading()) {
        <button (click)="createRun()">Start Simulation</button>
      }
      @if (error()) { <p class="error">{{ error() }}</p> }
    </div>
  `,
})
export class SimulationControlComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private svc = inject(SimulationService);

  scenarioId = '';
  run = signal<SimulationRun | null>(null);
  loading = signal(true);
  error = signal('');

  ngOnInit(): void {
    this.scenarioId = this.route.snapshot.paramMap.get('id') ?? '';
    this.loading.set(false);
  }

  createRun(): void {
    this.svc.create(this.scenarioId).subscribe({
      next: (r) => { this.run.set(r); this.router.navigate(['/simulations', r.id, 'dashboard']); },
      error: (e) => this.error.set(e.message),
    });
  }

  pause(): void { this.run()?.id && this.svc.pause(this.run()!.id).subscribe(); }
  resume(): void { this.run()?.id && this.svc.resume(this.run()!.id).subscribe(); }
  stop(): void { this.run()?.id && this.svc.stop(this.run()!.id).subscribe(); }
  start(): void { this.createRun(); }
}
