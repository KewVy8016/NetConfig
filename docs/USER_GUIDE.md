# คู่มือใช้งาน NetConfig ส่วนสำคัญ

คู่มือนี้อธิบายวิธีใช้แอปในแล็บ Cisco IOS โดยไม่สมมติว่ามี EVE-NG API ดูขอบเขตที่รองรับใน [FEATURES.md](FEATURES.md) และโครงสร้างระบบใน [ARCHITECTURE.md](ARCHITECTURE.md)

## 1. เตรียมก่อนเปิด

- เครื่องที่รัน backend ต้องเข้าถึง management IP/พอร์ต SSH หรือ Telnet ของอุปกรณ์ได้จริง; สำหรับ Serial ต้องมีช่องทาง Serial ที่ Netmiko ใช้ได้
- ติดตั้ง Python 3.11+, Node.js 18+ และ dependency ตาม [README.md](../README.md); ตั้งค่า `.env` ตาม `.env.example` โดยกำหนด `NETCONFIG_FERNET_KEY` ก่อนรัน backend และรักษา key เดิมไว้เพื่ออ่าน credential เดิม
- ให้ Cisco IOS มี username/password หรือ line password ตาม protocol ที่ใช้ รวมถึง enable secret หากงานนั้นต้องเข้า privileged mode
- แอปไม่มีระบบ login เว็บสำหรับหลายผู้ใช้ในรุ่นนี้ จึงควรใช้ในแล็บที่ควบคุมการเข้าถึงได้

บน Windows สามารถดับเบิลคลิก `run-netconfig.bat` ที่ root โครงการ สคริปต์จะเปิด backend ที่ `127.0.0.1:8000`, UI ที่ `http://127.0.0.1:5175/` และ browser หากพอร์ตนั้นมีบริการอยู่แล้วจะไม่เปิดซ้ำ ตรวจ backend ได้ที่ `http://127.0.0.1:8000/health`

ถ้าจะรันแยกเอง ให้เปิด backend จาก **root โครงการ** ด้วย `python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload` แล้วเปิด frontend ในโฟลเดอร์ `frontend` ด้วย `npm run dev` (ค่า Vite ปกติเป็นพอร์ต 5173) อย่าเปิด backend ซ้ำบนพอร์ต 8000

## 2. เพิ่ม Node และเข้าใจ Scan

1. กด **Add Node** แล้วกรอกชื่อที่ต้องการให้แสดงในระบบและเลือกชนิด Router/Switch ชื่อนี้เป็น alias ไม่จำเป็นต้องตรงกับ Hostname บนอุปกรณ์
2. ถ้าไม่ทราบ IP ให้เปิด **Scan** ในหน้า Add Node ใส่ subnet ขนาดเล็ก แล้วเลือกผลที่พบ ระบบจะเติม IP/port/transport ให้ตรวจทานก่อน
3. ในขั้น **Protocol** เลือก SSH, Telnet หรือ Serial แล้วกรอก endpoint/ข้อมูล login ตามรูปแบบอุปกรณ์: SSH ใช้ username/password; Telnet อนุญาตชื่อผู้ใช้ว่างเมื่อเป็น password-only; Serial จะแสดงพอร์ต COM/tty ที่เครื่อง backend ตรวจพบให้เลือกพร้อมชื่อสาย USB console กดรีเฟรชได้และยังกรอกเองได้; username/password เว้นว่างได้เมื่ออุปกรณ์ไม่ถาม
4. กด **Test Connection** ก่อนบันทึก สำหรับ SSH/Telnet ให้อ่านผล Ping, Port, Login และ Hostname; สำหรับ Serial ให้ตรวจผลการเปิดพอร์ต การเข้าสู่ระบบ และ Hostname (Ping/TCP port ไม่เกี่ยวกับสาย Console) หากขั้นใดล้มเหลว ให้แก้ข้อมูลเชื่อมต่อแล้ว Retry
5. เมื่อบันทึกสำเร็จ เปิดรายละเอียด Node เพื่อทำงานต่อ

Scan ตรวจเพียง port 22/23 ไม่รู้ชื่ออุปกรณ์, credential หรือ capability และไม่พบ switch L2 ที่ไม่มี management IP/Serial ให้ตั้ง management SVI/IP และทางกลับไปยังเครื่องที่รัน backend ก่อน หรือใช้ Serial ตามที่อุปกรณ์รองรับ การ Ping ผ่านไม่ได้แปลว่า SSH/Telnet login จะผ่าน

รายการ Serial มาจาก **เครื่องที่รัน backend** ซึ่งต้องเป็นเครื่องเดียวกับที่เสียบสาย USB console หรือมองเห็นพอร์ต Serial นั้น ถ้าเสียบสายใหม่ขณะเปิดฟอร์ม รายการจะตรวจซ้ำอัตโนมัติประมาณทุก 5 วินาที; กดรีเฟรชได้ทันที หากไม่พบพอร์ต ให้ตรวจสาย/ไดรเวอร์แล้วลองอีกครั้ง การเห็น COM port ยังไม่ยืนยันว่าเข้าถึง IOS ได้ ต้องกด Test Connection ก่อน Save

## 3. อ่านสถานะ Node

**Connected** คือผลทดสอบการเชื่อมต่อล่าสุดสำเร็จ; **Unreachable** คือการตรวจล่าสุดไม่ผ่าน; **Unknown** คือยังไม่มีผลที่ยืนยันได้หรืออ่านสถานะไม่ได้ สถานะไม่ใช่ session ที่เปิดค้าง หากเพิ่งเปลี่ยน network/device ให้กดทดสอบใหม่หรือรอรอบตรวจบน Dashboard/Node Detail (ประมาณ 30 วินาทีขณะเปิดหน้า) แล้วตรวจข้อความรายขั้น

คำอธิบายบน Dashboard และ Node Detail จึงใช้คำว่า “ผลตรวจล่าสุด” เพื่อไม่ให้เข้าใจว่า Connected หมายถึงระบบคง session กับอุปกรณ์ตลอดเวลา

หาก Port ผ่านแต่ Login ไม่ผ่าน ให้ตรวจชนิด protocol, credential และการตั้งค่า `line vty`/SSH ของ IOS; หาก PuTTY เข้าได้ แต่แอปไม่ได้ ให้เทียบ IP/port/transport และ prompt ที่อุปกรณ์แสดง ไม่ควรสรุปว่า network ใช้งานไม่ได้จาก error Login อย่างเดียว

## 4. ตั้ง Interface, Loopback และ Switch

เปิด Node Detail → **Interfaces** แล้วเลือก interface จากรายการ ระบบอ่านค่าปัจจุบันมาใส่ฟอร์มให้ตรวจทานก่อนเปลี่ยน IP/netmask/description หรือเปิด-ปิด port ปุ่มเปิด/ปิด port ใช้ได้แม้ interface ไม่มี IP การปิด port ที่ใช้บริหารอุปกรณ์อาจทำให้เชื่อมต่อไม่ได้ ควรตรวจ interface ที่เลือกก่อน Apply

ฟังก์ชัน Loopback และ Switch อยู่ในส่วนการตั้งค่าเพิ่มเติมของ Interface สำหรับ Switch มี access port/VLAN, SVI และ routed port โดย UI ตรวจ capability ที่อ่านได้จากอุปกรณ์ อย่าคาดว่าการเลือกชนิด “Switch” อย่างเดียวทำให้อุปกรณ์รองรับทุกคำสั่ง เมื่อแปลง routed port กลับ L2 ระบบคืน `switchport` เท่านั้น; ค่า access/trunk/VLAN/description/admin เดิมต้องตรวจและตั้งใหม่ตามต้องการ

## 5. ตั้ง Routing และดูค่าปัจจุบัน

สำหรับ Router เปิดแท็บ **Routing** แล้วเลือก Static/default route, RIP, OSPF, EIGRP หรือ BGP ฟอร์มจะรับพารามิเตอร์ที่จำเป็นและอ่าน state ที่มีอยู่จาก device เพื่อช่วยแก้หรือลบ อย่าพิมพ์ Cisco CLI ลงในฟอร์ม เพราะ CLI ถูกสร้างที่ backend จากข้อมูลที่ตรวจแล้ว หลัง Apply ให้ใช้แท็บ **Show** ตรวจ `show ip route`, `show ip protocols` หรือคำสั่ง neighbor ของ protocol นั้น และทดสอบการสื่อสารจริงเมื่อมี topology รองรับ

แท็บ Routing ไม่แสดงสำหรับ Node ที่บันทึกเป็น Switch; งาน L3 บางชนิดของ switch เช่น routed port/SVI อยู่ในส่วน Interface แทน

## 6. Preview, Apply และ Save Config

ทุกการเปลี่ยน configuration ผ่านสองจังหวะ:

1. กรอก/เลือกค่าแล้วกด **Preview**; อ่าน CLI และคำเตือน ตรวจชื่อ interface, IP, network, mask, ASN/process และผลกระทบให้ถูกต้อง ในขั้นนี้ยังไม่ส่งคำสั่งเปลี่ยนอุปกรณ์
2. กด **Apply** เพื่อส่งจริง ระบบแสดงผลรายคำสั่ง หากบางคำสั่งล้มเหลวให้ดูผลและตรวจ config จริงก่อนทำซ้ำ เพราะ Cisco IOS ไม่ย้อนคำสั่งที่สำเร็จแล้วอัตโนมัติ

Preview มีอายุ 5 นาที หากหมดอายุหรือแก้ฟอร์ม ให้สร้าง Preview ใหม่ การกด Apply เปลี่ยน running-config เท่านั้น; เมื่อตรวจแล้วว่าถูกต้องจึงใช้ปุ่ม **Save Config** แล้ว Preview/Apply `write memory` เพื่อเก็บค่าให้คงอยู่หลัง reboot

## 7. Show และ History

ในแท็บ **Show** เลือกคำสั่งจากรายการที่แอปอนุญาตเพื่อดูข้อมูลปัจจุบัน เช่น interface brief, route และ running-config ส่วน History แสดงสิ่งที่แอปส่งและผลลัพธ์ย้อนหลัง ไม่ใช่สำเนา config ปัจจุบัน

หน้า **History** กรองตาม Node, สถานะ และช่วงวันเวลาได้ ใช้ปุ่มก่อนหน้า/ถัดไปเพื่อเปลี่ยนหน้า และเปิดแถว/การ์ดเพื่อดูคำสั่ง ผลลัพธ์ และรหัสอ้างอิง หาก Node ถูกลบแล้ว รายการเก่าจะยังมีชื่อที่เก็บไว้ตอนบันทึก

เวลาที่กรองเป็นเวลาท้องถิ่นของเครื่องที่เปิดเว็บ และช่วง “ถึง” รวมเหตุการณ์ภายในนาทีที่เลือก ประวัติเป็นผลการดำเนินการในอดีต; หากต้องการยืนยันค่าปัจจุบัน ให้ใช้ Show อ่านจากอุปกรณ์อีกครั้ง

## 8. เมื่อใช้งานไม่สำเร็จ

| อาการ | ตรวจอย่างแรก |
|---|---|
| UI เปิดได้แต่เรียก backend ไม่ได้ | ดู `/health`, ตรวจว่า backend รันจาก root และพอร์ต 8000 ไม่มีโปรเซสอื่นใช้ |
| Scan ไม่พบ | เช็ก subnet, reachability และ TCP 22/23 จากเครื่อง backend; Scan ไม่ทดสอบ Serial หรือ login |
| Ping ผ่าน/Port เปิด แต่ Login timeout | เทียบ protocol, prompt, credential, line/SSH config และการรองรับอัลกอริทึม SSH ของ IOS รุ่นนั้น |
| Status ยังไม่เปลี่ยน | กด Test ใหม่หรือรอรอบตรวจ; ตรวจข้อความรายขั้น ไม่ยึดสีสถานะเก่าอย่างเดียว |
| Apply ล้มเหลวบางคำสั่ง | เปิดรายละเอียดผล/History แล้วใช้ Show อ่าน state จริง; แก้เฉพาะส่วนที่ยังไม่สำเร็จ |
| Config หายหลัง reboot | ตรวจว่าได้ใช้ Save Config (`write memory`) สำเร็จก่อน reboot |

สำหรับหลักฐาน manual EVE ที่ยังต้องทำ โดยเฉพาะ Loopback/Switch Phase 5 ให้ดู checklist ใน [TASKS.md](TASKS.md)
