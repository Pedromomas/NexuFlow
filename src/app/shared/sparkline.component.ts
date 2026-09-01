import { ChangeDetectionStrategy, Component, Input } from '@angular/core';

@Component({
  selector: 'app-sparkline',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <svg viewBox="0 0 240 72" preserveAspectRatio="none" class="sparkline" aria-hidden="true">
      <defs>
        <linearGradient [attr.id]="gradientId" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="currentColor" stop-opacity=".28" />
          <stop offset="1" stop-color="currentColor" stop-opacity="0" />
        </linearGradient>
      </defs>
      <path class="spark-fill" [attr.d]="fillPath" [attr.fill]="'url(#' + gradientId + ')'" />
      <path class="spark-line" [attr.d]="linePath" />
    </svg>
  `,
  styles: [`
    :host { display:block; width:100%; height:72px; color:var(--accent,#7c5cff); }
    .sparkline { width:100%; height:100%; overflow:visible; }
    .spark-line { fill:none; stroke:currentColor; stroke-width:2.25; vector-effect:non-scaling-stroke; filter:drop-shadow(0 0 5px currentColor); }
    .spark-fill { stroke:none; }
  `]
})
export class SparklineComponent {
  @Input() values: number[] = [];
  @Input() gradientId = 'sparkGradient';

  get linePath(): string {
    const pts = this.points;
    if (!pts.length) return '';
    return pts.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p[0].toFixed(2)} ${p[1].toFixed(2)}`).join(' ');
  }

  get fillPath(): string {
    const line = this.linePath;
    return line ? `${line} L 240 72 L 0 72 Z` : '';
  }

  private get points(): Array<[number, number]> {
    if (this.values.length < 2) return [];
    const min = Math.min(...this.values);
    const max = Math.max(...this.values);
    const range = Math.max(1, max - min);
    return this.values.map((v, i) => [
      (i / (this.values.length - 1)) * 240,
      64 - ((v - min) / range) * 52
    ]);
  }
}
