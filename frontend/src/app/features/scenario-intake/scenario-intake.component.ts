import { Component, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ScenarioService } from '../../core/services/scenario.service';

@Component({
  selector: 'app-scenario-intake',
  standalone: true,
  imports: [FormsModule],
  template: `
    <div class="intake-container">
      <h1>New Scenario</h1>
      <div class="form-section">
        <label>Name</label>
        <input [(ngModel)]="name" placeholder="Scenario name" />
        <label>Description</label>
        <textarea [(ngModel)]="description" placeholder="Optional description"></textarea>
        <label>Domain</label>
        <select [(ngModel)]="domain">
          @for (d of domains; track d) { <option [value]="d">{{ d }}</option> }
        </select>
        <label>Max Agents ({{ maxAgents }})</label>
        <input type="range" min="10" max="100" [(ngModel)]="maxAgents" />
        <label>Max Ticks ({{ maxTicks }})</label>
        <input type="range" min="5" max="30" [(ngModel)]="maxTicks" />
        <label>Random Seed</label>
        <input type="number" [(ngModel)]="seed" />
        <label>Source File</label>
        <input type="file" (change)="onFileChange($event)" accept=".pdf,.docx,.txt,.md" />
        @if (fileName()) { <span class="file-name">{{ fileName() }}</span> }
        <button (click)="create()" [disabled]="!name || loading()">
          {{ loading() ? 'Creating...' : 'Create & Compile World' }}
        </button>
        @if (error()) { <p class="error">{{ error() }}</p> }
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
    fd.append('config', JSON.stringify({ max_agents: this.maxAgents, max_ticks: this.maxTicks, random_seed: this.seed }));
    if (this.selectedFile) fd.append('file', this.selectedFile);

    this.svc.create(fd).subscribe({
      next: (scenario) => {
        if (scenario.source_file_path || this.selectedFile) {
          this.svc.compile(scenario.id).subscribe({
            next: () => this.router.navigate(['/scenarios', scenario.id, 'world']),
            error: (e) => { this.error.set(e.message); this.loading.set(false); },
          });
        } else {
          this.router.navigate(['/scenarios', scenario.id, 'world']);
        }
      },
      error: (e) => { this.error.set(e.message); this.loading.set(false); },
    });
  }
}
