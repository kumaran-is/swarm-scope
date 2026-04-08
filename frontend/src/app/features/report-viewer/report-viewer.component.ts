import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { CommonModule } from '@angular/common';
import { ReportService, Report } from '../../core/services/report.service';

@Component({
  selector: 'app-report-viewer',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="report-container">
      <header class="report-header">
        <h1>Simulation Report</h1>
        <span class="sim-id">Sim {{ simId }}</span>
        @if (!report() && !loading()) {
          <button class="generate-btn" (click)="generate()" [disabled]="generating()">
            {{ generating() ? 'Generating…' : 'Generate Report' }}
          </button>
        }
      </header>

      @if (loading()) {
        <p class="loading">Loading report…</p>
      } @else if (report(); as r) {
        <section class="summary-section">
          <h2>Executive Summary</h2>
          <p>{{ r.executive_summary ?? 'No summary available.' }}</p>
        </section>

        <section class="narrative-section">
          <h2>Narrative</h2>
          <p class="narrative">{{ r.narrative ?? 'No narrative available.' }}</p>
        </section>

        @if (r.key_findings && asArray(r.key_findings).length > 0) {
          <section class="findings-section">
            <h2>Key Findings</h2>
            <ul>
              @for (finding of asArray(r.key_findings); track $index) {
                <li>{{ finding }}</li>
              }
            </ul>
          </section>
        }

        <section class="timeline-section">
          <h2>Timeline</h2>
          @if (r.timeline.length > 0) {
            <div class="timeline">
              @for (event of r.timeline; track $index) {
                <div class="timeline-event">
                  <span class="event-dot"></span>
                  <span class="event-text">{{ asString(event) }}</span>
                </div>
              }
            </div>
          } @else {
            <p class="empty-state">No timeline events.</p>
          }
        </section>

        @if (r.counterfactual_notes) {
          <section class="counterfactual-section">
            <h2>Counterfactual Notes</h2>
            <p>{{ r.counterfactual_notes }}</p>
          </section>
        }

        <p class="generated-at">Generated: {{ r.created_at | date: 'medium' }}</p>
      } @else if (error()) {
        <p class="error">{{ error() }}</p>
      } @else {
        <div class="no-report">
          <p>No report generated yet.</p>
          <button class="generate-btn" (click)="generate()" [disabled]="generating()">
            {{ generating() ? 'Generating…' : 'Generate Report' }}
          </button>
        </div>
      }
    </div>
  `,
  styles: [`
    .report-container { padding: 1.5rem; max-width: 900px; }
    .report-header { display: flex; align-items: center; gap: 1rem; margin-bottom: 2rem; flex-wrap: wrap; }
    .sim-id { color: #888; font-size: 0.9rem; }
    .generate-btn { margin-left: auto; background: #7c3aed; color: #fff; border: none; border-radius: 6px; padding: 0.5rem 1rem; cursor: pointer; }
    .generate-btn:disabled { opacity: 0.5; cursor: not-allowed; }
    section { margin-bottom: 2rem; }
    h2 { font-size: 1rem; color: #7c3aed; margin-bottom: 0.75rem; border-bottom: 1px solid #2a2a3e; padding-bottom: 0.25rem; }
    .narrative { white-space: pre-wrap; line-height: 1.6; color: #ccc; }
    ul { padding-left: 1.5rem; }
    li { padding: 0.3rem 0; color: #ccc; }
    .timeline { display: flex; flex-direction: column; gap: 0.5rem; }
    .timeline-event { display: flex; align-items: flex-start; gap: 0.75rem; }
    .event-dot { width: 10px; height: 10px; border-radius: 50%; background: #7c3aed; margin-top: 4px; flex-shrink: 0; }
    .event-text { font-size: 0.9rem; color: #ccc; }
    .generated-at { color: #888; font-size: 0.8rem; text-align: right; }
    .loading, .error, .empty-state { color: #888; font-style: italic; }
    .error { color: #f44336; }
    .no-report { text-align: center; padding: 3rem; display: flex; flex-direction: column; align-items: center; gap: 1rem; color: #888; }
  `],
})
export class ReportViewerComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private reportService = inject(ReportService);

  simId = '';
  report = signal<Report | null>(null);
  loading = signal(false);
  generating = signal(false);
  error = signal('');

  ngOnInit(): void {
    this.simId = this.route.snapshot.paramMap.get('id') ?? '';
    this.loadReport();
  }

  loadReport(): void {
    this.loading.set(true);
    this.reportService.get(this.simId).subscribe({
      next: (r) => { this.loading.set(false); this.report.set(r); },
      error: () => { this.loading.set(false); },
    });
  }

  generate(): void {
    this.generating.set(true);
    this.error.set('');
    this.reportService.generate(this.simId).subscribe({
      next: () => {
        this.generating.set(false);
        // Poll after a delay for the generated report
        setTimeout(() => this.loadReport(), 3000);
      },
      error: (err: Error) => {
        this.generating.set(false);
        this.error.set(err.message);
      },
    });
  }

  asArray(val: unknown): unknown[] {
    return Array.isArray(val) ? val : [];
  }

  asString(val: unknown): string {
    return typeof val === 'string' ? val : JSON.stringify(val);
  }
}
