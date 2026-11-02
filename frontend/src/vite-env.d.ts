/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_LINZ_LDS_TILES_API_KEY?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
