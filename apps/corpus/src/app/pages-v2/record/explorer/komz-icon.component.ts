import { Component, Input } from '@angular/core';
@Component({ selector: 'kw-komz-icon', standalone: true, template: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path [attr.d]="path"/></svg>', styles: [':host{display:inline-flex;width:1.5em;height:1.5em;flex-shrink:0}svg{width:100%;height:100%}'] })
export class KomzIconComponent {
  @Input() name = 'grid';
  get path(): string { return this.paths[this.name] || this.paths['grid']; }
  readonly paths: Record<string, string> = {
    globe: 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0 M3 12h18 M12 3c-5 5-5 13 0 18 5-5 5-13 0-18',
    grid: 'M3 3h6v6H3z M15 3h6v6h-6z M3 15h6v6H3z M15 15h6v6h-6z',
    home: 'm3 11 9-8 9 8 M5 10v11h5v-7h4v7h5V10',
    user: 'M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0 M4 21v-3a8 8 0 0 1 16 0v3z',
    people: 'M10 7a3 3 0 1 1-6 0 3 3 0 0 1 6 0 M20 7a3 3 0 1 1-6 0 3 3 0 0 1 6 0 M1 20v-3a6 6 0 0 1 12 0v3 M15 12a6 6 0 0 1 8 5v3',
    bars: 'M4 21V14 M9 21V9 M14 21V4 M19 21V1',
    menu: 'M4 6h16 M4 12h16 M4 18h16',
    arrow: 'm10 5-7 7 7 7 M3 12h18',
    mic: 'M9 5a3 3 0 0 1 6 0v7a3 3 0 0 1-6 0z M5 10v2a7 7 0 0 0 14 0v-2 M12 19v3 M9 22h6',
    play: 'm8 4 12 8-12 8z', stop: 'M6 6h12v12H6z',
    pin: 'M19 10c0 5-7 12-7 12S5 15 5 10a7 7 0 0 1 14 0 M15 10a3 3 0 1 1-6 0 3 3 0 0 1 6 0',
    chat: 'M21 11a9 9 0 0 1-9 9 11 11 0 0 1-4-1l-6 3 2-6a9 9 0 1 1 17-5z',
    heart: 'M20 5c-3-3-6-1-8 1-2-2-5-4-8-1-5 5 2 11 8 16 6-5 13-11 8-16z',
    question: 'M6 7a6 6 0 0 1 12 0c0 4-6 4-6 8 M12 20h.01',
    handshake: 'm3 5 4-2 4 2 3-2 7 3-4 7-3-2-3 1-4-3-3 6-4-2z M7 9l5 9 3 1 4-4 M9 14l5 5 M4 13l-2 3 3 3 2-2',
    filters: 'M3 5h8 M15 5h6 M3 12h2 M9 12h12 M3 19h12 M19 19h2 M11 3v4 M5 10v4 M15 17v4',
    search: 'M17 10a7 7 0 1 1-14 0 7 7 0 0 1 14 0 M15 15l6 6',
    train: 'M5 4h14v14H5z M5 10h14 M8 2h8 M8 18l-3 4 M16 18l3 4 M8 14h1 M15 14h1',
    basket: 'M2 8h20l-3 13H5z M6 8l4-6 M18 8l-4-6 M8 12v5 M12 12v5 M16 12v5',
    leaf: 'M20 3c-13-2-20 15-8 17 8 2 10-9 8-17 M5 22l12-15',
    book: 'M12 5v17 M12 5C8 2 4 2 2 3v16c4-1 7 0 10 3 3-3 6-4 10-3V3c-2-1-6-1-10 2',
    computer: 'M2 3h20v14H2z M8 22h8 M12 17v5',
  };
}
