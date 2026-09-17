import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, Input } from '@angular/core';

@Component({
  selector: 'app-theme-companion', standalone: true, imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <svg *ngIf="kind === 'kiwi'" viewBox="0 0 300 160" aria-hidden="true">
      <path class="habitat" d="M5 150q140-32 290 0M20 147q-14-60 15-103m-12 77 30-17m-32-4L6 83m25-9 25-18M264 146q32-70 7-117m12 73-29-18m28-14 17-19" fill="none" stroke="#459b67" stroke-width="4"/>
      <g class="bird"><ellipse cx="132" cy="101" rx="45" ry="36" fill="#a5814f"/><path d="M103 82q55-6 44 40-33 0-44-40" fill="#795934"/><circle cx="172" cy="77" r="26" fill="#cfb57c"/><path d="m194 76 58 34-63-22" fill="#f2d396"/><circle cx="180" cy="72" r="6" fill="#182922"/><circle cx="182" cy="70" r="2" fill="white"/><path d="m110 134-5 13m39-15 7 14m-51 1h19m25 0h17" stroke="#d6b879" stroke-width="5" stroke-linecap="round"/><path d="M163 53q-9-29 8-34 7 25-8 34" fill="#a0ea60"/></g>
      <g class="chick"><ellipse cx="63" cy="131" rx="20" ry="16" fill="#b89862"/><circle cx="78" cy="120" r="13" fill="#dec38c"/><path d="m89 119 29 13-31-7" fill="#eed394"/><circle cx="83" cy="117" r="3" fill="#10261c"/></g>
      <g class="fireflies" fill="#d2ff90"><circle cx="66" cy="30" r="3"/><circle cx="228" cy="39" r="2"/><circle cx="116" cy="49" r="2"/></g>
    </svg>
    <svg *ngIf="kind === 'origin'" viewBox="0 0 300 160" aria-hidden="true">
      <g fill="none" stroke="#9b76e5"><ellipse cx="150" cy="91" rx="96" ry="26"/><ellipse class="orbit" cx="150" cy="91" rx="78" ry="47" transform="rotate(-24 150 91)"/><path d="M5 137h56l22-24m212 24h-56l-22-24"/></g>
      <g class="crystal"><path d="m150 17 35 68-35 60-35-60Z" fill="#b48aff"/><path d="m150 17 0 128-35-60Z" fill="#65459d"/><path d="m115 85 35 14 35-14" fill="none" stroke="#eee0ff" stroke-width="2"/><path d="m132 79 10 4m16 0 10-4" stroke="#90fcff" stroke-width="4"/></g>
      <g class="satellites" fill="#edc28d"><path d="m71 31 7 13-7 13-7-13Zm157 46 5 10-5 10-5-10Z"/><circle cx="205" cy="26" r="3"/></g>
    </svg>
    <svg *ngIf="kind === 'rio'" viewBox="0 0 300 160" aria-hidden="true">
      <path d="m1 125 56-69 46 44 52-76 58 57 33-39 53 81" fill="#1e4355"/>
      <g fill="#263549" stroke="#5dbace" stroke-width="1.5"><path d="M12 142V103h43v39m9 0V74h38v68m10 0V95h40v47m10 0V63h42v79m8 0V93h29v49m9 0V115h39v27"/></g>
      <g class="windows" fill="#ffc896"><path d="M25 112h8v10h-8zm50-28h8v10h-8zm100-12h8v10h-8zm47 32h8v10h-8zm-96 0h8v10h-8z"/></g>
      <path class="city-pulse" d="M3 144h50l15-15 21 22 20-33 13 26h53l19-20 18 20h82" stroke="#6eeeff" stroke-width="3" fill="none"/>
      <path d="M184 62V36" stroke="#ffa294" stroke-width="3"/><circle class="beacon" cx="184" cy="30" r="5" fill="#ff7464"/>
    </svg>`,
  styles: [`
    :host{display:block;width:220px;pointer-events:none}svg{display:block;width:100%;height:auto}
    .bird{animation:forage 5s ease-in-out 2;transform-origin:145px 137px}.chick{animation:hop 2.4s ease-in-out 3;transform-origin:64px 147px}.fireflies{animation:glimmer 3s ease-in-out 3}
    .crystal{animation:levitate 4s ease-in-out 3}.satellites{animation:glimmer 3s ease-in-out 3}.city-pulse{stroke-dasharray:420;animation:signal 3s ease-out 3}.beacon,.windows{animation:glimmer 2.5s ease-in-out 3}
    @keyframes forage{0%,100%{transform:rotate(0)}45%{transform:rotate(7deg)}}@keyframes hop{0%,80%,100%{transform:translateY(0)}90%{transform:translateY(-7px)}}@keyframes glimmer{50%{opacity:.35}}@keyframes levitate{50%{transform:translateY(-9px)}}@keyframes signal{0%{stroke-dashoffset:420}100%{stroke-dashoffset:0}}
    @media(prefers-reduced-motion:reduce){*{animation:none!important}}
    :host-context(.reduce-motion) *{animation:none!important}
  `]
})
export class ThemeCompanionComponent { @Input() kind = ''; }
