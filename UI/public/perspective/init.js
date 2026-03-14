import perspective from "./perspective.js";
import "./perspective-viewer.js";
import "./perspective-viewer-datagrid.js";
import "./perspective-viewer-d3fc.js";

window.__perspective = perspective;
window.dispatchEvent(new Event("perspective-ready"));
