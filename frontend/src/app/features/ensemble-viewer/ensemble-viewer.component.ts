import { Component, OnInit, inject, signal, ElementRef, ViewChild } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';
import * as d3 from 'd3';

interface EnsembleRun {
  id: string;
  scenario_id: string;
  ensemble_size: number;
  status: string;
  statistics: EnsembleStatistics | null;
  completed_runs: number;
}

interface EnsembleStatistics {
  kpi_statistics: Record<string, KpiStats>;
  completed_runs: number;
}

interface KpiStats {
  mean: number[];
  std: number[];
  ci_95_lower: number[];
  ci_95_upper: number[];
  robustness_score: number;
}

interface SimRun {
  id: string;
  random_seed: number;
  status: string;
  ensemble_seed_index: number;
  kpi_values?: Record<string, number>;
}

@Component({
  selector: 'app-ensemble-viewer',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="ensemble-container">
      <header class="ensemble-header">
        <h1>Ensemble Viewer</h1>
        <span class="ensemble-id">Ensemble {{ ensembleId.slice(0, 8) }}</span>
        <span class="status-badge" [class]="ensemble()?.status ?? ''">
          {{ ensemble()?.status ?? 'Loading…' }}
        </span>
      </header>

      @if (loading()) {
        <p class="loading">Loading ensemble data…</p>
      } @else if (ensemble(); as e) {
        <!-- Section 1: Robustness Summary -->
        <section class="summary-section">
          <div class="robustness-card">
            <div class="gauge-label">Robustness Score</div>
            <div class="gauge-value">{{ (robustnessScore() * 100) | number: '1.0-0' }}%</div>
            <div class="gauge-bar">
              <div class="gauge-fill" [style.width.%]="robustnessScore() * 100"
                   [class.high]="robustnessScore() > 0.7" [class.medium]="robustnessScore() > 0.4 && robustnessScore() <= 0.7"></div>
            </div>
          </div>
          <div class="meta-grid">
            <div class="meta-item">
              <span class="meta-label">Runs</span>
              <span class="meta-value">{{ e.completed_runs }} / {{ e.ensemble_size }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">Most Stable KPI</span>
              <span class="meta-value">{{ mostStableKpi() ?? '—' }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">Most Variable KPI</span>
              <span class="meta-value">{{ mostVariableKpi() ?? '—' }}</span>
            </div>
          </div>
        </section>

        <!-- Section 2: KPI Confidence Band Chart -->
        @if (kpiEntries().length > 0) {
          <section class="kpi-section">
            <h2>KPI Confidence Bands</h2>
            <div class="kpi-tabs">
              @for (entry of kpiEntries(); track entry.name) {
                <button class="tab" [class.active]="selectedKpi() === entry.name"
                        (click)="selectKpi(entry.name)">{{ entry.name }}</button>
              }
            </div>
            <svg #chartSvg class="confidence-chart"></svg>
          </section>
        }

        <!-- Section 3: Run Comparison Table -->
        @if (runs().length > 0) {
          <section class="runs-section">
            <h2>Run Comparison</h2>
            <table class="runs-table">
              <thead>
                <tr>
                  <th>Run #</th>
                  <th>Seed</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                @for (run of runs(); track run.id) {
                  <tr>
                    <td>{{ run.ensemble_seed_index + 1 }}</td>
                    <td class="mono">{{ run.random_seed }}</td>
                    <td><span class="status-badge" [class]="run.status">{{ run.status }}</span></td>
                    <td><a [routerLink]="['/simulations', run.id, 'dashboard']" class="view-link">View</a></td>
                  </tr>
                }
              </tbody>
            </table>
          </section>
        }

      } @else if (error()) {
        <p class="error">{{ error() }}</p>
      }
    </div>
  `,
  styles: [`
    .ensemble-container { padding: 1.5rem; max-width: 1000px; }
    .ensemble-header { display: flex; align-items: center; gap: 1rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
    .ensemble-id { color: #888; font-size: 0.9rem; font-family: monospace; }
    .status-badge { padding: 0.25rem 0.75rem; border-radius: 999px; font-size: 0.8rem; background: #2a2a3e; }
    .status-badge.running { background: #7c3aed; color: #fff; }
    .status-badge.completed { background: #4caf50; color: #fff; }
    .status-badge.failed { background: #f44336; color: #fff; }
    .summary-section { display: flex; gap: 1.5rem; margin-bottom: 2rem; flex-wrap: wrap; }
    .robustness-card { background: #1e1e2e; border-radius: 10px; padding: 1.25rem; min-width: 200px; }
    .gauge-label { font-size: 0.8rem; color: #888; margin-bottom: 0.5rem; }
    .gauge-value { font-size: 2.5rem; font-weight: 700; margin-bottom: 0.5rem; }
    .gauge-bar { height: 8px; background: #2a2a3e; border-radius: 4px; overflow: hidden; }
    .gauge-fill { height: 100%; background: #f44336; border-radius: 4px; transition: width 0.5s; }
    .gauge-fill.medium { background: #ff9800; }
    .gauge-fill.high { background: #4caf50; }
    .meta-grid { display: flex; flex-direction: column; gap: 0.75rem; background: #1e1e2e; border-radius: 10px; padding: 1.25rem; flex: 1; }
    .meta-item { display: flex; justify-content: space-between; }
    .meta-label { color: #888; font-size: 0.85rem; }
    .meta-value { font-weight: 600; font-size: 0.9rem; }
    .kpi-section, .runs-section { margin-bottom: 2rem; }
    h2 { font-size: 1rem; color: #7c3aed; margin-bottom: 1rem; border-bottom: 1px solid #2a2a3e; padding-bottom: 0.25rem; }
    .kpi-tabs { display: flex; gap: 0.5rem; margin-bottom: 1rem; flex-wrap: wrap; }
    .tab { background: #1e1e2e; border: none; border-radius: 6px; padding: 0.4rem 0.9rem; cursor: pointer; color: #ccc; font-size: 0.85rem; }
    .tab.active { background: #7c3aed; color: #fff; }
    .confidence-chart { width: 100%; height: 280px; display: block; background: #1e1e2e; border-radius: 8px; }
    .runs-table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
    .runs-table th { text-align: left; padding: 0.5rem 0.75rem; border-bottom: 2px solid #2a2a3e; color: #888; font-size: 0.8rem; }
    .runs-table td { padding: 0.5rem 0.75rem; border-bottom: 1px solid #1a1a2a; }
    .mono { font-family: monospace; }
    .view-link { color: #7c3aed; text-decoration: none; font-size: 0.85rem; }
    .loading, .error { color: #888; font-style: italic; }
    .error { color: #f44336; }
  `],
})
export class EnsembleViewerComponent implements OnInit {
  @ViewChild('chartSvg') chartSvg?: ElementRef<SVGElement>;

  private route = inject(ActivatedRoute);
  private api = inject(ApiService);

  ensembleId = '';
  ensemble = signal<EnsembleRun | null>(null);
  runs = signal<SimRun[]>([]);
  loading = signal(false);
  error = signal('');
  selectedKpi = signal('');

  kpiEntries = signal<{ name: string; stats: KpiStats }[]>([]);
  robustnessScore = signal(0);
  mostStableKpi = signal<string | null>(null);
  mostVariableKpi = signal<string | null>(null);

  ngOnInit(): void {
    this.ensembleId = this.route.snapshot.paramMap.get('id') ?? '';
    this.loadEnsemble();
    this.loadRuns();
  }

  loadEnsemble(): void {
    this.loading.set(true);
    this.api.get<EnsembleRun>(`/ensembles/${this.ensembleId}`).subscribe({
      next: (e) => {
        this.loading.set(false);
        this.ensemble.set(e);
        if (e.statistics?.kpi_statistics) {
          const entries = Object.entries(e.statistics.kpi_statistics).map(([name, stats]) => ({ name, stats }));
          this.kpiEntries.set(entries);

          // Robustness: average across KPIs
          const scores = entries.map((en) => en.stats.robustness_score ?? 0);
          this.robustnessScore.set(scores.length > 0 ? scores.reduce((a, b) => a + b) / scores.length : 0);

          // Most stable / most variable
          const sorted = [...entries].sort((a, b) => (b.stats.robustness_score ?? 0) - (a.stats.robustness_score ?? 0));
          this.mostStableKpi.set(sorted[0]?.name ?? null);
          this.mostVariableKpi.set(sorted[sorted.length - 1]?.name ?? null);

          if (entries.length > 0) {
            this.selectedKpi.set(entries[0].name);
            setTimeout(() => this.renderChart(), 100);
          }
        }
      },
      error: (err: Error) => {
        this.loading.set(false);
        this.error.set(err.message);
      },
    });
  }

  loadRuns(): void {
    this.api.get<SimRun[]>(`/ensembles/${this.ensembleId}/runs`).subscribe({
      next: (runs) => this.runs.set(runs),
      error: () => {},
    });
  }

  selectKpi(name: string): void {
    this.selectedKpi.set(name);
    setTimeout(() => this.renderChart(), 50);
  }

  private renderChart(): void {
    const svgEl = this.chartSvg?.nativeElement;
    if (!svgEl) return;

    const kpiName = this.selectedKpi();
    const entry = this.kpiEntries().find((e) => e.name === kpiName);
    if (!entry) return;

    const { mean, ci_95_lower, ci_95_upper } = entry.stats;
    const n = mean.length;
    if (!n) return;

    d3.select(svgEl).selectAll('*').remove();

    const width = svgEl.clientWidth || 800;
    const height = 280;
    const margin = { top: 20, right: 20, bottom: 30, left: 40 };

    const svg = d3.select(svgEl).attr('viewBox', `0 0 ${width} ${height}`);

    const xScale = d3.scaleLinear().domain([0, n - 1]).range([margin.left, width - margin.right]);
    const allVals = [...mean, ...(ci_95_lower ?? []), ...(ci_95_upper ?? [])];
    const yScale = d3.scaleLinear()
      .domain([d3.min(allVals) ?? 0, d3.max(allVals) ?? 100])
      .nice()
      .range([height - margin.bottom, margin.top]);

    // CI area
    if (ci_95_lower && ci_95_upper) {
      const area = d3.area<number>()
        .x((_d, i) => xScale(i))
        .y0((_d, i) => yScale(ci_95_lower[i]))
        .y1((_d, i) => yScale(ci_95_upper[i]))
        .curve(d3.curveCatmullRom);

      svg.append('path')
        .datum(mean)
        .attr('fill', '#7c3aed')
        .attr('fill-opacity', 0.2)
        .attr('d', area);
    }

    // Mean line
    const line = d3.line<number>()
      .x((_d, i) => xScale(i))
      .y((d) => yScale(d))
      .curve(d3.curveCatmullRom);

    svg.append('path')
      .datum(mean)
      .attr('fill', 'none')
      .attr('stroke', '#7c3aed')
      .attr('stroke-width', 2.5)
      .attr('d', line);

    // Axes
    svg.append('g')
      .attr('transform', `translate(0,${height - margin.bottom})`)
      .call(d3.axisBottom(xScale).ticks(Math.min(n, 8)).tickFormat((d) => `T${d}`))
      .call((g) => g.select('.domain').attr('stroke', '#444'))
      .call((g) => g.selectAll('text').attr('fill', '#888'));

    svg.append('g')
      .attr('transform', `translate(${margin.left},0)`)
      .call(d3.axisLeft(yScale).ticks(5))
      .call((g) => g.select('.domain').attr('stroke', '#444'))
      .call((g) => g.selectAll('text').attr('fill', '#888'));
  }
}
