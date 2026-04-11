import {
  ChangeDetectionStrategy,
  Component,
  CUSTOM_ELEMENTS_SCHEMA,
  ElementRef,
  input,
  OnInit,
  ViewChild,
  output,
} from '@angular/core';
import { ensurePerspectiveLoaded, PERSPECTIVE_THEMES } from '../perspective/perspective-loader';

type PerspectiveViewerElement = HTMLElement & {
  load: (client: unknown) => Promise<void>;
  resetThemes: (themes: string[]) => Promise<void>;
  restore: (config: object) => Promise<void>;
};

type PerspectiveClientRuntime = {
  websocket: (url: string) => Promise<unknown>;
};

@Component({
  selector: 'app-perspective-viewer-host',
  imports: [],
  schemas: [CUSTOM_ELEMENTS_SCHEMA],
  templateUrl: './perspective-viewer-host.html',
  styleUrl: './perspective-viewer-host.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PerspectiveViewerHostComponent implements OnInit {
  @ViewChild('viewer', { static: true })
  viewerRef!: ElementRef<HTMLElement>;

  readonly assetBasePath = input('perspective');
  readonly table = input('fx_executions');
  readonly websocketUrl = input<string | null>(null);
  readonly statusChange = output<string>();

  private client: unknown;

  async ngOnInit(): Promise<void> {
    this.statusChange.emit('Connecting...');

    try {
      await ensurePerspectiveLoaded(this.assetBasePath());
    } catch (err) {
      console.error('Failed to load Perspective scripts:', err);
      this.statusChange.emit('Load Error');
      return;
    }

    const viewer = this.viewerRef.nativeElement as PerspectiveViewerElement;
    const wsUrl = this.websocketUrl() ?? `ws://${window.location.hostname}:8080/websocket`;

    try {
      const perspective = (window as Window & { __perspective?: PerspectiveClientRuntime }).__perspective;

      if (!perspective) {
        throw new Error('Perspective runtime is unavailable after bootstrap');
      }

      this.client = await perspective.websocket(wsUrl);
      await viewer.load(this.client);
      await viewer.resetThemes([...PERSPECTIVE_THEMES]);
      await viewer.restore({
        table: this.table(),
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
      this.statusChange.emit('Connected');
    } catch (err) {
      console.error('Failed to connect to Perspective server:', err);
      this.statusChange.emit('Disconnected');
    }
  }
}

