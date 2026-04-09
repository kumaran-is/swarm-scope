import { Component, OnInit, OnDestroy, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { Subscription, interval } from 'rxjs';
import { switchMap, takeWhile } from 'rxjs/operators';
import { CommonModule } from '@angular/common';
import { ReportService, Report } from '../../core/services/report.service';

@Component({
  selector: 'app-report-viewer',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="report-container animate-fade-up">
      <div class="breadcrumbs text-xs mb-5">
        <ul>
          <li><a [routerLink]="['/scenarios']" style="color: var(--ss-text-muted);">Scenarios</a></li>
          <li><a [routerLink]="['/simulations', simId, 'dashboard']" style="color: var(--ss-text-muted);">Live Dashboard</a></li>
          <li style="color: var(--ss-text-secondary);">Report</li>
        </ul>
      </div>

      <header class="flex items-center gap-3 mb-8 flex-wrap">
        <h1 class="text-2xl font-bold tracking-tight" style="color: var(--ss-text-primary);">Simulation Report</h1>
        <span class="px-2 py-0.5 rounded text-xs mono-data" style="color: var(--ss-text-muted);">Sim {{ simId }}</span>
        <div class="ml-auto">
          @if (report()) {
            <button class="regen-btn" (click)="generate()">Regenerate</button>
          }
        </div>
      </header>

      @if (loading()) {
        <div class="flex items-center gap-3 py-8">
          <div class="w-5 h-5 rounded-full border-2 border-transparent animate-spin"
            style="border-top-color: var(--ss-cyan);"></div>
          <span class="text-sm" style="color: var(--ss-text-muted);">Loading report…</span>
        </div>
      } @else if (report(); as r) {

        <!-- Executive Summary -->
        <section class="report-section summary-card">
          <div class="section-title">Executive Summary</div>
          <p class="text-sm leading-relaxed" style="color: var(--ss-text-secondary);">
            {{ r.executive_summary ?? 'No summary available.' }}
          </p>
        </section>

        <!-- Narrative -->
        <section class="report-section glass-card p-5">
          <div class="section-title">Narrative</div>
          <p class="narrative-text">{{ r.narrative ?? 'No narrative available.' }}</p>
        </section>

        <!-- Key Findings -->
        @if (r.key_findings && asArray(r.key_findings).length > 0) {
          <section class="report-section glass-card p-5">
            <div class="section-title">Key Findings</div>
            <ul class="findings-list">
              @for (finding of asArray(r.key_findings); track $index) {
                <li class="finding-item">
                  <span class="finding-bullet">&#9654;</span>
                  <span>{{ finding }}</span>
                </li>
              }
            </ul>
          </section>
        }

        <!-- Timeline -->
        <section class="report-section glass-card p-5">
          <div class="section-title">Timeline</div>
          @if (r.timeline.length > 0) {
            <div class="timeline">
              @for (event of r.timeline; track $index) {
                <div class="timeline-event">
                  <div class="timeline-dot"></div>
                  <div class="timeline-line" [class.hidden]="$last"></div>
                  <span class="timeline-text">{{ asString(event) }}</span>
                </div>
              }
            </div>
          } @else {
            <p class="text-sm" style="color: var(--ss-text-muted); font-style: italic;">No timeline events.</p>
          }
        </section>

        <!-- Counterfactual -->
        @if (r.counterfactual_notes) {
          <section class="report-section glass-card p-5">
            <div class="section-title">Counterfactual Notes</div>
            <p class="text-sm leading-relaxed" style="color: var(--ss-text-secondary);">{{ r.counterfactual_notes }}</p>
          </section>
        }

        <p class="text-right text-xs mt-6 mono-data" style="color: var(--ss-text-muted);">
          Generated: {{ r.created_at | date: 'medium' }}
        </p>

      } @else if (generating()) {
        <!-- Generating overlay -->
        <div class="generating-state">
          <div class="scan-box">
            <div class="scan-ring"></div>
            <div class="scan-inner-ring"></div>
          </div>
          <p class="text-sm font-medium" style="color: var(--ss-cyan);">Generating report with Gemini AI…</p>
          <p class="text-xs mono-data" style="color: var(--ss-text-muted);">
            This takes 30–60 seconds &nbsp;·&nbsp; Check {{ pollAttempts() }}/24
          </p>
          <div class="generating-progress">
            <div class="generating-fill" [style.width.%]="(pollAttempts() / 24) * 100"></div>
          </div>
        </div>
      } @else if (error()) {
        <div class="empty-state-center">
          <div class="text-2xl mb-3" style="color: var(--ss-error);">&#9888;</div>
          <p class="text-sm mb-4" style="color: var(--ss-error);">{{ error() }}</p>
          <button class="generate-btn" (click)="generate()">Try Again</button>
        </div>
      } @else {
        <div class="empty-state-center">
          <div class="w-16 h-16 rounded-full flex items-center justify-center text-3xl mb-4"
            style="background: var(--ss-cyan-dim); border: 1px solid rgba(6,182,212,0.2);">
            &#128196;
          </div>
          <p class="text-sm mb-6" style="color: var(--ss-text-muted);">No report generated yet.</p>
          <button class="generate-btn" (click)="generate()">Generate Report</button>
        </div>
      }
    </div>
  `,
  styles: [`
    .report-container { padding: 1.5rem; max-width: 860px; }

    .report-section { margin-bottom: 1.25rem; }

    .summary-card {
      background: var(--ss-bg-card);
      border: 1px solid var(--ss-border);
      border-left: 3px solid var(--ss-cyan);
      border-radius: 12px;
      padding: 1.25rem 1.5rem;
      background: linear-gradient(90deg, rgba(6,182,212,0.04), var(--ss-bg-card));
    }

    .section-title {
      font-size: 0.75rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--ss-cyan);
      margin-bottom: 0.75rem;
    }

    .narrative-text {
      white-space: pre-wrap;
      line-height: 1.7;
      font-size: 0.875rem;
      color: var(--ss-text-secondary);
    }

    .findings-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 0.5rem; }
    .finding-item { display: flex; align-items: flex-start; gap: 0.625rem; font-size: 0.875rem; color: var(--ss-text-secondary); }
    .finding-bullet { color: var(--ss-cyan); font-size: 0.6rem; margin-top: 5px; flex-shrink: 0; }

    .timeline { display: flex; flex-direction: column; gap: 0; }
    .timeline-event { display: flex; align-items: flex-start; gap: 0.875rem; position: relative; padding-bottom: 1rem; }
    .timeline-dot {
      width: 10px; height: 10px; border-radius: 50%;
      background: var(--ss-cyan);
      box-shadow: 0 0 6px rgba(6,182,212,0.5);
      flex-shrink: 0; margin-top: 4px;
    }
    .timeline-line {
      position: absolute;
      left: 4px; top: 14px; bottom: 0;
      width: 1px;
      background: var(--ss-border);
    }
    .timeline-text { font-size: 0.875rem; color: var(--ss-text-secondary); line-height: 1.5; }

    .regen-btn {
      background: transparent;
      color: var(--ss-cyan);
      border: 1px solid rgba(6,182,212,0.3);
      border-radius: 8px;
      padding: 0.375rem 0.875rem;
      font-size: 0.8rem;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.15s ease;
    }
    .regen-btn:hover { background: var(--ss-cyan-dim); }

    .generate-btn {
      background: linear-gradient(135deg, var(--ss-cyan), var(--ss-blue));
      color: #fff;
      border: none;
      border-radius: 10px;
      padding: 0.625rem 1.5rem;
      font-size: 0.875rem;
      font-weight: 600;
      cursor: pointer;
      transition: box-shadow 0.2s ease;
    }
    .generate-btn:hover { box-shadow: var(--ss-glow-cyan); }

    .generating-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 1rem;
      padding: 4rem 2rem;
    }
    .scan-box { position: relative; width: 80px; height: 80px; display: flex; align-items: center; justify-content: center; }
    .scan-ring {
      width: 80px; height: 80px; border-radius: 50%;
      border: 2px solid rgba(6,182,212,0.3);
      animation: pulse-ring 2s ease-in-out infinite;
    }
    .scan-inner-ring {
      position: absolute;
      width: 50px; height: 50px; border-radius: 50%;
      border: 2px solid var(--ss-cyan);
      animation: pulse-ring 2s ease-in-out infinite 0.5s;
    }
    .generating-progress {
      width: 200px; height: 3px;
      background: var(--ss-border); border-radius: 2px;
    }
    .generating-fill {
      height: 100%;
      background: linear-gradient(90deg, var(--ss-cyan), var(--ss-blue));
      border-radius: 2px;
      transition: width 0.5s ease;
    }

    .empty-state-center {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 4rem 2rem;
      text-align: center;
    }
  `],
})
export class ReportViewerComponent implements OnInit, OnDestroy {
  private route = inject(ActivatedRoute);
  private reportService = inject(ReportService);

  simId = '';
  report = signal<Report | null>(null);
  loading = signal(false);
  generating = signal(false);
  error = signal('');
  pollAttempts = signal(0);

  private pollSub?: Subscription;

  ngOnInit(): void {
    this.simId = this.route.snapshot.paramMap.get('id') ?? '';
    this.loadReport();
  }

  ngOnDestroy(): void {
    this.pollSub?.unsubscribe();
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
    this.pollAttempts.set(0);
    this.reportService.generate(this.simId).subscribe({
      next: () => {
        // Poll every 5s for up to 2 minutes (24 attempts)
        this.pollSub?.unsubscribe();
        this.pollSub = interval(5000).pipe(
          takeWhile(() => !this.report() && this.pollAttempts() < 24),
        ).subscribe(() => {
          this.pollAttempts.update(n => n + 1);
          this.reportService.get(this.simId).subscribe({
            next: (r) => {
              this.generating.set(false);
              this.report.set(r);
              this.pollSub?.unsubscribe();
            },
            error: () => {
              // 404 means still generating — keep polling
              if (this.pollAttempts() >= 24) {
                this.generating.set(false);
                this.error.set('Report generation timed out. Try again.');
              }
            },
          });
        });
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
