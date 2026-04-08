import {
  Component,
  ElementRef,
  Input,
  OnChanges,
  OnDestroy,
  OnInit,
  Output,
  EventEmitter,
  ViewChild,
  SimpleChanges,
} from '@angular/core';
import * as d3 from 'd3';

export interface GraphNode {
  id: string;
  label: string;
  type: 'entity' | 'faction';
  group?: string;
  size?: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  label?: string;
  type?: 'tension' | 'alliance' | 'resource_flow';
  weight?: number;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

@Component({
  selector: 'app-knowledge-graph-viewer',
  standalone: true,
  template: `<svg #svgEl style="width:100%;height:100%;display:block;"></svg>`,
  styles: [`:host { display: block; width: 100%; height: 100%; min-height: 400px; }`],
})
export class KnowledgeGraphViewerComponent implements OnInit, OnChanges, OnDestroy {
  @Input() data: GraphData = { nodes: [], edges: [] };
  @Output() nodeClicked = new EventEmitter<GraphNode>();

  @ViewChild('svgEl', { static: true }) svgRef!: ElementRef<SVGSVGElement>;

  private simulation: d3.Simulation<d3.SimulationNodeDatum, undefined> | null = null;
  private resizeObserver: ResizeObserver | null = null;

  ngOnInit(): void {
    this.resizeObserver = new ResizeObserver(() => this.render());
    this.resizeObserver.observe(this.svgRef.nativeElement.parentElement!);
    this.render();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['data']) {
      this.render();
    }
  }

  ngOnDestroy(): void {
    this.simulation?.stop();
    this.resizeObserver?.disconnect();
  }

  private edgeColor(type: string | undefined): string {
    switch (type) {
      case 'tension': return '#f44336';
      case 'alliance': return '#4caf50';
      case 'resource_flow': return '#2196f3';
      default: return '#888';
    }
  }

  private render(): void {
    const el = this.svgRef.nativeElement;
    const width = el.clientWidth || 800;
    const height = el.clientHeight || 500;

    d3.select(el).selectAll('*').remove();

    if (!this.data.nodes.length) return;

    const svg = d3.select(el)
      .attr('viewBox', `0 0 ${width} ${height}`)
      .call(
        d3.zoom<SVGSVGElement, unknown>().on('zoom', (event) => {
          g.attr('transform', event.transform);
        }) as never
      );

    const g = svg.append('g');

    // Defensive copy for D3 mutation
    const nodes = this.data.nodes.map((n) => ({ ...n, x: width / 2, y: height / 2 }));
    const nodeMap = new Map(nodes.map((n) => [n.id, n]));

    const links = this.data.edges
      .filter((e) => nodeMap.has(e.source) && nodeMap.has(e.target))
      .map((e) => ({ ...e }));

    this.simulation?.stop();
    this.simulation = d3.forceSimulation(nodes as d3.SimulationNodeDatum[])
      .force('link', d3.forceLink(links).id((d: d3.SimulationNodeDatum) => (d as GraphNode).id).distance(120))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2));

    // Draw edges
    const link = g.append('g').selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke', (d) => this.edgeColor(d.type))
      .attr('stroke-width', (d) => Math.max(1, (d.weight ?? 0.5) * 2))
      .attr('stroke-opacity', 0.7);

    // Draw nodes
    const node = g.append('g').selectAll('circle')
      .data(nodes)
      .join('circle')
      .attr('r', (d) => d.type === 'faction' ? (d.size ?? 14) : (d.size ?? 10))
      .attr('fill', (d) => d.type === 'faction' ? '#7c3aed' : '#60a5fa')
      .attr('stroke', '#fff')
      .attr('stroke-width', 1.5)
      .style('cursor', 'pointer')
      .on('click', (_event, d) => {
        this.nodeClicked.emit(d as unknown as GraphNode);
      })
      .call(
        d3.drag<SVGCircleElement, unknown>()
          .on('start', (event) => {
            if (!event.active) this.simulation!.alphaTarget(0.3).restart();
            (event.subject as { fx: number; fy: number }).fx = (event.subject as { x: number }).x;
            (event.subject as { fx: number; fy: number }).fy = (event.subject as { y: number }).y;
          })
          .on('drag', (event) => {
            (event.subject as { fx: number; fy: number }).fx = event.x;
            (event.subject as { fx: number; fy: number }).fy = event.y;
          })
          .on('end', (event) => {
            if (!event.active) this.simulation!.alphaTarget(0);
            (event.subject as { fx: null; fy: null }).fx = null;
            (event.subject as { fx: null; fy: null }).fy = null;
          }) as never
      );

    // Labels
    const label = g.append('g').selectAll('text')
      .data(nodes)
      .join('text')
      .text((d) => d.label)
      .attr('font-size', '10px')
      .attr('fill', '#ccc')
      .attr('text-anchor', 'middle')
      .attr('dy', (d) => (d.size ?? 10) + 14)
      .style('pointer-events', 'none');

    // Tooltip
    const tooltip = d3.select('body').append('div')
      .style('position', 'fixed')
      .style('background', '#1e1e2e')
      .style('border', '1px solid #444')
      .style('border-radius', '6px')
      .style('padding', '6px 10px')
      .style('font-size', '12px')
      .style('color', '#ccc')
      .style('pointer-events', 'none')
      .style('opacity', '0');

    node
      .on('mouseover', (event, d) => {
        tooltip.style('opacity', '1')
          .html(`<strong>${(d as GraphNode).label}</strong><br/>${(d as GraphNode).type}`)
          .style('left', `${event.clientX + 10}px`)
          .style('top', `${event.clientY - 28}px`);
      })
      .on('mouseout', () => tooltip.style('opacity', '0'));

    this.simulation.on('tick', () => {
      link
        .attr('x1', (d) => ((d.source as unknown as { x: number }).x))
        .attr('y1', (d) => ((d.source as unknown as { y: number }).y))
        .attr('x2', (d) => ((d.target as unknown as { x: number }).x))
        .attr('y2', (d) => ((d.target as unknown as { y: number }).y));

      node
        .attr('cx', (d) => (d as { x: number }).x)
        .attr('cy', (d) => (d as { y: number }).y);

      label
        .attr('x', (d) => (d as { x: number }).x)
        .attr('y', (d) => (d as { y: number }).y);
    });

    // Cleanup tooltip on destroy
    el.addEventListener('remove', () => tooltip.remove(), { once: true });
  }
}
