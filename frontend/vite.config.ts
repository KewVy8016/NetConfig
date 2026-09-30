// แยกการเปิดหน้า React ออกจาก API ที่ใช้เส้นทาง /nodes และ /history ร่วมกัน
import { defineConfig, type ProxyOptions } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// การรีเฟรช/เปิด URL โดยตรงต้องได้ HTML; API และ WebSocket ยังไป backend
const bypassPageNavigation: ProxyOptions['bypass'] = (request) => {
  if (request.method === 'GET' && !request.headers.upgrade && request.headers.accept?.includes('text/html')) {
    return '/index.html'
  }
}

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/nodes': { target: 'http://127.0.0.1:8000', ws: true, bypass: bypassPageNavigation },
      '/history': { target: 'http://127.0.0.1:8000', bypass: bypassPageNavigation },
      '/health': 'http://127.0.0.1:8000',
    },
  },
})
