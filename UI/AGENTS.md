# AGENTS.md - FX Executions Blotter (Angular + Perspective)

## Big picture

Angular 21 standalone app with one route-less page:
`AppComponent` -> `BlotterComponent` -> `PerspectiveViewerHostComponent` -> `<perspective-viewer>` web component.

Market data is not fetched via REST. The host opens a WebSocket client to the external Python Perspective server:
`ws://<host>:8080/websocket`.

## Perspective runtime loading (critical)

- Runtime JS/CSS/WASM is sourced from `node_modules/@perspective-dev/*` via `angular.json` asset globs, emitted to `/perspective` and `/wasm` at build time.
- `public/` copy excludes `perspective/**` and `wasm/**` to avoid stale vendored files overriding package assets.
- Use `ensurePerspectiveLoaded()` in `src/app/perspective/perspective-loader.ts` to bootstrap Perspective once.
- Loader behavior:
  - injects required CSS links (`icons`, `intl`, themes, plugin styles)
  - injects a module script that imports `perspective.js`, `perspective-viewer.js`, and plugins
  - sets `window.__perspective` and dispatches `perspective-ready`
- Do not import `@perspective-dev/*` directly in Angular components; use the loader + `window.__perspective` runtime.

## Component pattern

- `PerspectiveViewerHostComponent` (`src/app/perspective-viewer-host/perspective-viewer-host.ts`) is the reusable host.
- Required for custom element template parsing: `schemas: [CUSTOM_ELEMENTS_SCHEMA]`.
- Generic inputs:
  - `assetBasePath` (default `perspective`)
  - `table` (default `fx_executions`)
  - `websocketUrl` (defaults to host `:8080/websocket`)
- Emits status via `statusChange` (`Connecting...`, `Connected`, `Disconnected`, `Load Error`).
- Default `viewer.restore()` config uses `Datagrid`, theme `Pro Dark`, 15 execution columns, sorted by `exec_time desc`.

## Build and dev workflows

```bash
npm start
npm run build
npm run watch
npm test
```

- App runs on `http://localhost:4200`; Perspective backend must already be running on `:8080`.
- Schematics are configured with `skipTests: true` in `angular.json`.

## Styling and layout conventions

- SCSS everywhere (`style": "scss"` schematics setting).
- Global shell sizing is in `src/styles.scss` (`html/body` full-height, overflow hidden).
- Blotter/host styles use flex full-bleed layout; preserve this when adding views.

## Key files

- `src/app/perspective/perspective-loader.ts` - generic runtime loader and theme list.
- `src/app/perspective-viewer-host/perspective-viewer-host.ts` - reusable WebSocket + viewer host.
- `src/app/blotter/blotter.ts` - page-level status wiring around the host.
- `angular.json` - asset pipeline from `node_modules` to `/perspective` and `/wasm`.
- `src/index.html` - minimal shell only; Perspective CSS is now runtime-injected.

