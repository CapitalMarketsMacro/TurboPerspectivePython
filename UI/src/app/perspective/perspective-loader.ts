const CORE_STYLE_FILES = [
  'icons.css',
  'intl.css',
  'perspective-viewer-datagrid.css',
  'perspective-viewer-d3fc.css',
];

const THEME_STYLE_FILES = [
  'pro.css',
  'pro-dark.css',
  'solarized.css',
  'solarized-dark.css',
  'monokai.css',
  'vaporwave.css',
  'botanical.css',
  'dracula.css',
  'gruvbox.css',
  'gruvbox-dark.css',
];

const LOADER_ID = 'perspective-runtime-loader';
const READY_EVENT = 'perspective-ready';

type PerspectiveRuntime = {
  websocket: (url: string) => Promise<unknown>;
};

type PerspectiveWindow = Window & {
  __perspective?: PerspectiveRuntime;
  __perspectiveLoaderPromise?: Promise<void>;
};

function toAssetBasePath(assetBasePath: string): string {
  return assetBasePath.replace(/\/+$/, '');
}

function ensureStyles(assetBasePath: string): void {
  const files = [...CORE_STYLE_FILES, ...THEME_STYLE_FILES];

  for (const fileName of files) {
    const href = `${assetBasePath}/${fileName}`;
    const existing = document.querySelector(`link[data-perspective-style="${href}"]`);

    if (existing) {
      continue;
    }

    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = href;
    link.crossOrigin = 'anonymous';
    link.dataset['perspectiveStyle'] = href;
    document.head.appendChild(link);
  }
}

function buildModuleBootstrapSource(assetBasePath: string): string {
  return [
    `import perspective from '${assetBasePath}/perspective.js';`,
    `import '${assetBasePath}/perspective-viewer.js';`,
    `import '${assetBasePath}/perspective-viewer-datagrid.js';`,
    `import '${assetBasePath}/perspective-viewer-d3fc.js';`,
    'window.__perspective = perspective;',
    `window.dispatchEvent(new Event('${READY_EVENT}'));`,
  ].join('\n');
}

export const PERSPECTIVE_THEMES = [
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
] as const;

export function ensurePerspectiveLoaded(assetBasePath = 'perspective'): Promise<void> {
  const runtimeWindow = window as PerspectiveWindow;

  if (runtimeWindow.__perspective) {
    return Promise.resolve();
  }

  if (runtimeWindow.__perspectiveLoaderPromise) {
    return runtimeWindow.__perspectiveLoaderPromise;
  }

  const normalizedAssetBasePath = toAssetBasePath(assetBasePath);
  ensureStyles(normalizedAssetBasePath);

  runtimeWindow.__perspectiveLoaderPromise = new Promise((resolve, reject) => {
    const onReady = () => resolve();
    window.addEventListener(READY_EVENT, onReady, { once: true });

    const existingScript = document.getElementById(LOADER_ID) as HTMLScriptElement | null;
    if (existingScript) {
      return;
    }

    const script = document.createElement('script');
    script.id = LOADER_ID;
    script.type = 'module';
    script.textContent = buildModuleBootstrapSource(normalizedAssetBasePath);
    script.onerror = () => {
      window.removeEventListener(READY_EVENT, onReady);
      runtimeWindow.__perspectiveLoaderPromise = undefined;
      reject(new Error('Failed to load Perspective runtime assets'));
    };

    document.head.appendChild(script);
  });

  return runtimeWindow.__perspectiveLoaderPromise;
}
