import { Component, CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { BlotterComponent } from './blotter/blotter';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [BlotterComponent],
  schemas: [CUSTOM_ELEMENTS_SCHEMA],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {}
