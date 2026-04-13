/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_ADMIN_CONFIG_KEY?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
