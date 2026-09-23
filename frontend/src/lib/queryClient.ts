// TanStack Query client configuration สำหรับ NetConfig
// กำหนด retry, stale time และ error handling เริ่มต้น

import { QueryClient } from '@tanstack/react-query'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // ลอง refetch 1 ครั้งเมื่อ error (ไม่ retry network error ซ้ำเกิน)
      retry: 1,
      retryDelay: 1000,
      // ข้อมูล node status เปลี่ยนได้ทุกเวลา ตั้ง stale เร็ว
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 0,
    },
  },
})
