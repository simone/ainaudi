import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react({
      include: '**/*.{jsx,js}',
    }),
    // Custom plugin to handle /media/ requests before SPA fallback
    {
      name: 'media-proxy-plugin',
      configureServer(server) {
        server.middlewares.use((req, res, next) => {
          if (req.url && req.url.startsWith('/media/')) {
            console.log('🔍 Media middleware intercepted:', req.url);
            // Let the proxy handle it, don't fall back to index.html
            next();
          } else {
            next();
          }
        });
      },
    },
  ],
  esbuild: {
    loader: 'jsx',
    include: /src\/.*\.jsx?$/,
    exclude: [],
  },
  optimizeDeps: {
    esbuildOptions: {
      loader: {
        '.js': 'jsx',
        '.jsx': 'jsx',
      },
    },
  },
  server: {
    port: 3000,
    host: '0.0.0.0', // Allow external connections in Docker
    proxy: {
      '/api': {
        // Use VITE_BACKEND_URL from env, fallback to localhost
        target: process.env.VITE_BACKEND_URL || 'http://localhost:3001',
        changeOrigin: true,
        secure: false,
        configure: (proxy, options) => {
          console.log('🔧 Vite Proxy /api configured:', options.target);
          proxy.on('error', (err, req, res) => {
            console.log('❌ Proxy error:', err.message);
          });
          proxy.on('proxyReq', (proxyReq, req, res) => {
            console.log('→ Proxying:', req.method, req.url, 'to', options.target);
          });
        }
      },
      '/media': {
        // Proxy media files (uploaded PDFs, images, etc.)
        target: process.env.VITE_BACKEND_URL || 'http://localhost:3001',
        changeOrigin: true,
        secure: false,
        ws: false,
        configure: (proxy, options) => {
          console.log('🔧 Vite Proxy /media configured:', options.target);

          proxy.on('error', (err, req, res) => {
            console.error('❌ Media proxy error:', err.message);
          });

          proxy.on('proxyReq', (proxyReq, req, res) => {
            console.log('📁 Proxying media:', req.method, req.url, 'to', options.target);
          });

          proxy.on('proxyRes', (proxyRes, req, res) => {
            console.log('✅ Media proxy response:', req.url, 'status:', proxyRes.statusCode);
          });
        }
      },
    },
  },
  build: {
    outDir: 'build',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          charts: ['chart.js', 'react-chartjs-2'],
        },
      },
    },
  },
  define: {
    // Make environment variables available
    'process.env': {},
  },
})
