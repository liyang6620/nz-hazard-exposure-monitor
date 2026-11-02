/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_REVIEW_API_BASE_URL?: string;
  readonly VITE_LINZ_LDS_TILES_API_KEY?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
