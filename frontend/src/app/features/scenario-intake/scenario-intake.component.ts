import { Component, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ScenarioService } from '../../core/services/scenario.service';

@Component({
  selector: 'app-scenario-intake',
  standalone: true,
  imports: [FormsModule],
  template: `
    <div class="max-w-2xl mx-auto">
      <div class="mb-6">
        <h1 class="text-3xl font-bold">New Scenario</h1>
        <p class="text-base-content/60 mt-1">Configure your simulation and upload a source document</p>
      </div>

      <div class="card bg-base-200 border border-base-300 shadow-lg">
        <div class="card-body gap-5">

          <fieldset class="fieldset">
            <label class="fieldset-label">
              Scenario Name <span class="text-error">*</span>
            </label>
            <input class="input input-bordered w-full"
              [(ngModel)]="name" placeholder="e.g. Climate Policy 2035" />
          </fieldset>

          <fieldset class="fieldset">
            <label class="fieldset-label">Description</label>
            <textarea class="textarea textarea-bordered w-full"
              [(ngModel)]="description"
              placeholder="Optional — describe the scenario context and goals"
              rows="3"></textarea>
          </fieldset>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <fieldset class="fieldset">
              <label class="fieldset-label">Domain</label>
              <select class="select select-bordered w-full" [(ngModel)]="domain">
                @for (d of domains; track d) {
                  <option [value]="d">{{ d }}</option>
                }
              </select>
            </fieldset>

            <fieldset class="fieldset">
              <label class="fieldset-label">Random Seed</label>
              <input class="input input-bordered w-full" type="number" [(ngModel)]="seed" />
            </fieldset>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <fieldset class="fieldset">
              <label class="fieldset-label flex justify-between">
                Max Agents
                <span class="badge badge-primary badge-sm">{{ maxAgents }}</span>
              </label>
              <input class="range range-primary range-sm" type="range"
                min="10" max="100" step="5" [(ngModel)]="maxAgents" />
              <div class="flex justify-between text-xs text-base-content/40 mt-1">
                <span>10</span><span>100</span>
              </div>
            </fieldset>

            <fieldset class="fieldset">
              <label class="fieldset-label flex justify-between">
                Max Ticks
                <span class="badge badge-secondary badge-sm">{{ maxTicks }}</span>
              </label>
              <input class="range range-secondary range-sm" type="range"
                min="5" max="30" step="1" [(ngModel)]="maxTicks" />
              <div class="flex justify-between text-xs text-base-content/40 mt-1">
                <span>5</span><span>30</span>
              </div>
            </fieldset>
          </div>

          <fieldset class="fieldset">
            <label class="fieldset-label">Source Document</label>
            <label class="border-2 border-dashed border-base-300 rounded-xl p-6 flex flex-col items-center gap-2 cursor-pointer hover:border-primary hover:bg-base-300/30 transition-all">
              <input type="file" class="hidden"
                (change)="onFileChange($event)" accept=".pdf,.docx,.txt,.md" />
              <span class="text-3xl">&#128196;</span>
              @if (fileName()) {
                <span class="text-primary font-medium text-sm">{{ fileName() }}</span>
              } @else {
                <span class="text-base-content/40 text-sm text-center">
                  Click to upload PDF, DOCX, TXT, or MD<br/>
                  <span class="text-xs">Max 50 MB</span>
                </span>
              }
            </label>
          </fieldset>

          @if (error()) {
            <div class="alert alert-error text-sm">
              <span>{{ error() }}</span>
            </div>
          }

          <div class="card-actions justify-end mt-2">
            <button class="btn btn-primary btn-wide"
              (click)="create()" [disabled]="!name || loading()">
              @if (loading()) {
                <span class="loading loading-spinner loading-sm"></span>
              }
              {{ loading() ? 'Compiling World\u2026' : 'Create & Compile World' }}
            </button>
          </div>

        </div>
      </div>
    </div>
  `,
})
export class ScenarioIntakeComponent {
  private svc = inject(ScenarioService);
  private router = inject(Router);

  name = '';
  description = '';
  domain = 'general';
  maxAgents = 20;
  maxTicks = 15;
  seed = Math.floor(Math.random() * 100000);
  domains = ['general', 'policy', 'org_change', 'crisis', 'market', 'fiction'];
  selectedFile: File | null = null;
  fileName = signal('');
  loading = signal(false);
  error = signal('');

  onFileChange(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files?.length) {
      this.selectedFile = input.files[0];
      this.fileName.set(input.files[0].name);
    }
  }

  create(): void {
    this.loading.set(true);
    this.error.set('');
    const fd = new FormData();
    fd.append('name', this.name);
    if (this.description) fd.append('description', this.description);
    fd.append('domain', this.domain);
    fd.append('config', JSON.stringify({
      max_agents: this.maxAgents,
      max_ticks: this.maxTicks,
      random_seed: this.seed,
    }));
    if (this.selectedFile) fd.append('file', this.selectedFile);

    this.svc.create(fd).subscribe({
      next: (scenario) => {
        if (scenario.source_file_path || this.selectedFile) {
          this.svc.compile(scenario.id).subscribe({
            next: () => this.router.navigate(['/scenarios', scenario.id, 'world']),
            error: (e: Error) => { this.error.set(e.message); this.loading.set(false); },
          });
        } else {
          this.router.navigate(['/scenarios', scenario.id, 'world']);
        }
      },
      error: (e: Error) => { this.error.set(e.message); this.loading.set(false); },
    });
  }
}
