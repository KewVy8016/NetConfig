# NetConfig

NetConfig คือ Web UI สำหรับตั้งค่า Cisco IOS IPv4 ผ่าน SSH, Telnet และ Serial โดยมอง EVE-NG เป็นเครือข่ายจริง

## การติดตั้งและการรัน

### ความต้องการของระบบ
- Python 3.11+
- Node.js 18+

### อุปกรณ์ที่รับรอง (EVE-NG / Hardware)
- **Cisco IOS (vIOS-L2/L3)**: แนะนำให้ใช้ Image vIOS-L3 (Software version 15.6+)
- รองรับการเชื่อมต่อผ่าน:
  - SSH (port 22)
  - Telnet (port 23)
  - Serial (e.g. COM3)
- Backend pin `Paramiko >=3.4,<4.0` เพื่อรองรับ SSH ของ IOSv รุ่นเก่าร่วมกับ Netmiko 4.3;
  Paramiko 5 ตัด legacy SSH algorithms ที่ image บางรุ่นยังต้องใช้ จึงทำให้ TCP 22 เปิดแต่
  session ไม่ถึง IOS prompt

### วิธีการติดตั้ง
1. **ตั้งค่า Backend**:
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # หรือ .venv\Scripts\activate สำหรับ Windows
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```
2. **ตั้งค่า Environment Variables**:
   สร้างไฟล์ `.env` ใน root directory โดยใช้ `.env.example` เป็นต้นแบบ
   ```bash
   cp .env.example .env
   ```
   **คำเตือน**: ต้องมีตัวแปร `NETCONFIG_FERNET_KEY` เพื่อใช้ในการเข้ารหัส credential

3. **ตั้งค่า Frontend**:
   ```bash
   cd frontend
   npm install
   ```

### วิธีการรัน
เปิด 2 Terminal เพื่อรันแยกกัน

บน Windows สามารถดับเบิลคลิก [`run-netconfig.bat`](run-netconfig.bat) เพื่อเปิด Backend,
Frontend และ Browser พร้อมกันได้ในครั้งเดียว; หาก Backend/Frontend รันอยู่แล้ว สคริปต์จะใช้
process เดิม ไม่เปิดซ้ำจนพอร์ตชนกัน

**1. Backend**:
```bash
# ต้องรันจาก project root เพื่อให้ import package `backend` และโหลด .env ถูกต้อง
cd "D:\งานเอกสาร\KMUTNB document\Netprograming APP\NetConfig"
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
Backend จะทำงานที่ `http://localhost:8000`

**2. Frontend**:
```bash
cd frontend
npm run dev
```
Frontend จะทำงานที่ `http://localhost:5173`

## ทดสอบ (Tests)
รัน test สำหรับ backend (พร้อม mock Netmiko) ด้วยคำสั่ง:
```bash
cd backend
pytest tests/ -v
```

## ความสามารถที่สาธิตได้

- `POST /nodes/test` — ทดสอบ typed payload ก่อนบันทึก; หาก test ไม่ผ่านจะไม่สร้าง node ในฐานข้อมูล
- Telnet รองรับทั้ง login แบบ username/password และแบบ password-only (เว้น Username ว่างได้)
- Serial console รองรับการเชื่อมต่อโดยไม่กรอก Username/Password เมื่ออุปกรณ์ไม่ถาม credential
- `POST /nodes/{id}/config/interface/preview` — validate และ render คำสั่งโดยยังไม่ส่ง device
- `POST /nodes/{id}/config/interface/apply` — apply ด้วย `operation_id` และ `payload_hash` จาก preview
- `GET /nodes/{id}/show?command=...` — Show command จาก allowlist พร้อม raw/parsed output
- `GET /history` — command history แบบ filter ด้วย `node_id` และ `overall_status`
- `POST /nodes/scan` — ค้นหาเฉพาะ TCP 22/23 ใน IPv4 subnet ขนาดไม่เกิน `/28`; เลือกผลเพื่อ prefill Add Node หรือกรอก IP เองได้
- Routing: Static/default route, RIP, OSPF, EIGRP และ BGP ผ่าน form แยก resource, preview และ Apply
- `Save Config` — สร้าง preview ของ `write memory` ก่อน จากนั้นต้องยืนยันอีกครั้งใน drawer แล้วจึง Apply; ระบบไม่บันทึก startup-config อัตโนมัติ

## ขั้นตอนสาธิตบน EVE-NG

1. เปิด R2 และ R3 ให้ management IP reachable จาก Windows host แล้วเพิ่ม Node ผ่าน SSH หรือ Telnet
2. ที่ Add Node เลือก Scan subnet (เช่น `192.168.8.128/28`) หรือกรอก IP เอง จากนั้นกรอก credential และกด Test Connection
3. บันทึก Node ได้เมื่อ Ping, Port, Login และ Hostname ผ่านครบเท่านั้น
4. หน้า Node Detail เลือก Interfaces เพื่อดูรายการจากอุปกรณ์และตั้ง IPv4 ผ่าน Preview → Apply
5. เลือก Routing เพื่อสาธิต Static, RIP, OSPF, EIGRP หรือ BGP; ทุก protocol มี Remove action และผลอยู่ใน Command History
6. เมื่อพอใจกับ running-config แล้ว กด Save Config → ตรวจ command preview → Apply → ยืนยัน dialog เพื่อรัน `write memory`

## การแก้ปัญหาเบื้องต้น

- Ping ผ่านแต่ Login ไม่ผ่าน: ตรวจ transport/port, credential และ Enable Secret; SSH ของ IOSv เก่าอาจต้องใช้ Paramiko 3.x ตาม requirements
- หน้า Node แสดง Unreachable: กด Reconnect เพื่อทดสอบ Ping → Port → Login → Hostname ใหม่ แล้วดูขั้นที่ล้มเหลว
- Add Node บันทึกไม่ได้: ระบบตั้งใจไม่สร้าง Node เมื่อ Test Connection ไม่ผ่าน; แก้ค่าและ Retry ก่อน
- Preview หมดอายุหรือ Node Busy: Refresh actual state แล้วสร้าง Preview ใหม่ เพราะ Apply จะยอมรับเฉพาะ operation/hash ที่ยัง valid
- BGP neighbor ยังไม่รับ prefix: ตรวจ local/remote AS, IP link, advertised network ต้องมีอยู่ใน routing table และรอ BGP converge ช่วงสั้น ๆ

ฟอร์มตั้งค่าผ่าน Preview → Apply; แท็บ CLI เปิด session แยกสำหรับแล็บและส่งคำสั่งทีละบรรทัดทันที พร้อม audit ผลใน History โดยไม่เก็บเนื้อหาคำสั่งหรือ output ที่อาจมีรหัสผ่าน. Console ที่สั่ง `enable` โดยไม่ถามรหัสใช้งานได้โดยไม่กรอก Enable Secret.
