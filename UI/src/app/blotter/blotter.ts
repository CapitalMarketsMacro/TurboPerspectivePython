import {
  Component,
  CUSTOM_ELEMENTS_SCHEMA,
  ElementRef,
  OnDestroy,
  OnInit,
  ViewChild,
} from '@angular/core';

function loadPerspective(): Promise<void> {
  return new Promise((resolve, reject) => {
    // Listen for the custom event that init.js dispatches after all imports resolve
    window.addEventListener('perspective-ready', () => resolve(), { once: true });

    const script = document.createElement('script');
    script.type = 'module';
    script.src = 'perspective/init.js';
    script.onerror = () => reject(new Error('Failed to load Perspective'));
    document.head.appendChild(script);
  });
}

@Component({
  selector: 'app-blotter',
  standalone: true,
  schemas: [CUSTOM_ELEMENTS_SCHEMA],
  templateUrl: './blotter.html',
  styleUrl: './blotter.scss',
})
export class BlotterComponent implements OnInit, OnDestroy {
  @ViewChild('viewer', { static: true })
  viewerRef!: ElementRef<HTMLElement>;

  private client: any;
  status = 'Loading...';

  async ngOnInit(): Promise<void> {
    try {
      await loadPerspective();
    } catch (err) {
      console.error('Failed to load Perspective scripts:', err);
      this.status = 'Load Error';
      return;
    }

    const viewer = this.viewerRef.nativeElement as any;
    const wsUrl = `ws://${window.location.hostname}:8080/websocket`;
    this.status = 'Connecting...';

    try {
      const perspective = (window as any).__perspective;
      this.client = await perspective.websocket(wsUrl);
      await viewer.load(this.client);
      await viewer.resetThemes([
        'Pro Light',
        'Pro Dark',
        'Solarized',
        'Solarized Dark',
        'Monokai',
        'Vaporwave',
        'Botanical',
        'Dracula',
        'Gruvbox',
        'Gruvbox Dark',
      ]);
      await viewer.restore({
        table: 'fx_executions',
        plugin: 'Datagrid',
        theme: 'Pro Dark',
        columns: [
          'trade_id',
          'exec_time',
          'ccy_pair',
          'side',
          'notional',
          'rate',
          'spot_rate',
          'pnl',
          'venue',
          'trader_id',
          'desk',
          'status',
          'counterparty',
          'value_date',
          'sequence_num',
        ],
        sort: [['exec_time', 'desc']],
      });
      this.status = 'Connected';
    } catch (err) {
      console.error('Failed to connect to Perspective server:', err);
      this.status = 'Disconnected';
    }
  }

  ngOnDestroy(): void {
    // viewer handles cleanup on DOM removal
  }
}
