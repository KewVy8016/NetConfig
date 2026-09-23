# NetConfig — Demo Script สำหรับ EVE-NG

ใช้สาธิตฟังก์ชัน Assignment แบบไม่พึ่ง EVE API. ให้เปิด backend และ frontend ตาม `README.md`
ก่อนเริ่ม และตรวจว่า R2/R3 management IP reachable จาก Windows host.

## Topology ที่ใช้ทดสอบ

| Node | Management | Transport | Link | Loopback |
|---|---|---|---|---|
| R2 | `192.168.8.135` | Telnet 23 | Gi0/1 `10.0.23.1/30` | `2.2.2.2/32` |
| R3 | `192.168.8.136` | SSH 22 | Et0/1 `10.0.23.2/30` | `3.3.3.3/32` |

## ลำดับสาธิต

1. เปิด Dashboard: ใช้ Search, สลับ Cards/Table และยืนยันสถานะ Connected หรือ Unreachable
   ที่ refresh ทุก 30 วินาที.
2. เปิด Add Node: ที่ Protocol เลือก Scan subnet `192.168.8.128/28`, กด Scan SSH/Telnet,
   เลือกผลที่พบเพื่อ prefill หรือกรอก management IP เอง. ทำ Test Connection แล้ว Save ได้เฉพาะ
   เมื่อ Ping/Port/Login/Hostname ผ่าน.
3. เปิด R2 > Interfaces: เลือก interface จาก dropdown, ตรวจ prefill actual state, ตั้ง
   `10.0.23.1/30` แล้ว Preview → Apply. ทำฝั่ง R3 เป็น `10.0.23.2/30` และยืนยัน ping.
4. Static route: เพิ่ม test route บน R2, ตรวจ `show ip route` และ Command History, จากนั้น
   Delete ผ่าน Preview → Apply เพื่อคืน state.
5. RIP, OSPF, EIGRP: ตั้ง protocol เดียวทั้ง R2/R3, advertise link `10.0.23.0/30` และ
   loopback ฝั่งตนเอง, ตรวจ neighbor/route ผ่าน Show, แล้ว Remove Protocol ทั้งสองฝั่ง.
6. BGP: เพิ่ม neighbor R2 AS 65002 → R3 AS 65003 และย้อนกลับ, advertise loopback ของแต่ละฝั่ง,
   รอ summary รับ prefix แล้ว Remove Protocol ทั้งสองฝั่ง.
7. Save Config: กด Save Config จาก Node Detail, อ่าน `write memory` ใน preview, กด Apply และ
   ยืนยัน dialog. ตรวจ history ประเภท `Save Configuration`.

## หลักฐานที่ต้องเก็บ

- Screenshot หน้า Add Node (scan/manual/test success), Routing preview, Show neighbor/route และ History
- ผล `show ip interface brief`, `show ip route`, `show ip ospf neighbor`,
  `show ip eigrp neighbors`, `show ip bgp summary`
- ผล `pytest backend/tests -q`, `ruff check backend`, `mypy backend`, `npm run build`

## Cleanup

ลบ static route และ Remove Protocol ทั้งคู่ผ่าน UI. การเปลี่ยน interface/loopback ที่ต้องการ
เก็บต่อสามารถใช้ Save Config แบบ explicit; ไม่มี workflow ใดบันทึก startup-config อัตโนมัติ.
