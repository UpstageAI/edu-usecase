import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  define: {
    'process.env.DATA_SOURCE': JSON.stringify(process.env.DATA_SOURCE || 'mock')
  }
});

