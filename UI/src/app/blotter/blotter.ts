import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { PerspectiveViewerHostComponent } from '../perspective-viewer-host/perspective-viewer-host';

@Component({
  selector: 'app-blotter',
  imports: [PerspectiveViewerHostComponent],
  templateUrl: './blotter.html',
  styleUrl: './blotter.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BlotterComponent {
  readonly status = signal('Loading...');

  onStatusChange(status: string): void {
    this.status.set(status);
  }
}
