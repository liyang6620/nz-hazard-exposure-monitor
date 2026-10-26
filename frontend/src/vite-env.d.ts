/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_LINZ_BASEMAPS_API_KEY?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
