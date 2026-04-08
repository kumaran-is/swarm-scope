import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink, RouterModule } from '@angular/router';
import { CommonModule } from '@angular/common';
import { SimulationService, SimulationRun } from '../../core/services/simulation.service';

@Component({
  selector: 'app-simulation-control',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterModule],
  template: `
    <div class="max-w-2xl mx-auto py-12 px-4">
      <div class="text-sm breadcrumbs mb-4">
        <ul>
          <li><a routerLink="/scenarios">Scenarios</a></li>
          <li><a [routerLink]="['/scenarios', scenarioId, 'world']">World Model</a></li>
          <li>Simulation Control</li>
        </ul>
      </div>
      <h1 class="text-2xl font-bold mb-6">Simulation Control</h1>

      @if (run()) {
        <div class="flex gap-6 mb-6 bg-base-200 rounded-lg p-4">
          <span>Status: <strong class="text-primary">{{ run()!.status }}</strong></span>
          <span>Tick: {{ run()!.current_tick }} / {{ run()!.max_ticks }}</span>
        </div>
        <div class="flex gap-3 mb-8">
          <button class="btn btn-primary" (click)="start()" [disabled]="run()!.status === 'running'">Start</button>
          <button class="btn btn-outline" (click)="pause()" [disabled]="run()!.status !== 'running'">Pause</button>
          <button class="btn btn-outline" (click)="resume()" [disabled]="run()!.status !== 'paused'">Resume</button>
          <button class="btn btn-error btn-outline" (click)="stop()">Stop</button>
        </div>
        <div class="flex gap-4 flex-wrap">
          <a class="btn btn-ghost btn-sm" [routerLink]="['/simulations', run()!.id, 'dashboard']">Live Dashboard</a>
          <a class="btn btn-ghost btn-sm" [routerLink]="['/simulations', run()!.id, 'intervene']">Interventions</a>
          <a class="btn btn-ghost btn-sm" [routerLink]="['/simulations', run()!.id, 'chat']">Agent Chat</a>
          <a class="btn btn-ghost btn-sm" [routerLink]="['/simulations', run()!.id, 'report']">Report</a>
        </div>
      }

      @if (!run() && !loading()) {
        <p class="text-base-content/60 mb-6">Agent generation is running in the background. You can start the simulation now — it will wait for agents to be ready.</p>
        <button class="btn btn-primary btn-lg" (click)="createRun()">
          Start Simulation
        </button>
      }

      @if (loading()) {
        <span class="loading loading-spinner loading-md"></span>
      }

      @if (error()) {
        <div class="alert alert-error mt-4">{{ error() }}</div>
      }
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
