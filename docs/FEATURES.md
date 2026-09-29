# ฟีเจอร์และขอบเขตของ NetConfig

เอกสารนี้สรุป **สิ่งที่มีอยู่ในโค้ดปัจจุบัน** (29 กันยายน 2026) แยกจากสิ่งที่ยังต้องตรวจด้วยอุปกรณ์จริงหรือยังเป็นแผนงาน อ่านวิธีใช้ที่ [USER_GUIDE.md](USER_GUIDE.md) และการไหลของระบบที่ [ARCHITECTURE.md](ARCHITECTURE.md)

## NetConfig ทำอะไร

NetConfig เป็นเว็บแอปสำหรับจัดการ Cisco IOS ในแล็บผ่าน management IP/พอร์ตของอุปกรณ์ โดยเชื่อมต่อด้วย SSH, Telnet หรือ Serial ผ่าน Netmiko โปรแกรม **ไม่อ่าน topology หรือข้อมูลจาก EVE-NG API**; EVE-NG ทำหน้าที่เป็นเครือข่ายที่อุปกรณ์อยู่เท่านั้น ขอบเขตหลักคือ IPv4, routing พื้นฐาน, switch L2/L3 บางส่วน, คำสั่ง Show และประวัติการทำงาน

## ฟีเจอร์ที่ใช้งานได้ในโค้ด

| ส่วน | ความสามารถ | ข้อสังเกต |
|---|---|---|
| Dashboard / Nodes | ดูรายการ, ค้นหาด้วยชื่อหรือ IP, เปิดรายละเอียด, ทดสอบการเชื่อมต่อใหม่และลบ Node | สถานะอิงผลตรวจล่าสุด ไม่ใช่การเปิด session ค้าง; หน้า Dashboard และรายละเอียดตรวจซ้ำทุก 30 วินาทีขณะเปิดอยู่ |
| Add Node | Wizard 3 ขั้น: ข้อมูลอุปกรณ์ → Protocol → Test & Save; รองรับ Router/Switch และ SSH/Telnet/Serial | หน้า UI จะให้บันทึกหลังทดสอบผ่าน; ขั้นทดสอบแสดง Ping, port, login, hostname |
| Scan ก่อน Add | สแกน subnet ขนาดเล็กจาก popup แล้วเลือก IP/transport มาช่วยกรอก | ตรวจเพียง TCP 22/23 จึงยังไม่รู้ชนิดอุปกรณ์หรือ credential และไม่พบ Serial/อุปกรณ์ที่ไม่มี management IP |
| ค้นหาพอร์ต USB Console | เมื่อเลือก Serial แสดง COM/tty ที่เครื่อง backend ตรวจพบพร้อมคำอธิบาย, รีเฟรชอัตโนมัติ/ด้วยปุ่ม และเลือกมาเติมฟอร์ม | ยังมีช่องกรอกเอง; การพบพอร์ตไม่ได้ยืนยันว่า login เข้า IOS ได้ |
| Interface | อ่านรายการ interface และค่าปัจจุบันจากอุปกรณ์เพื่อเลือกและเติมฟอร์ม; ตั้ง IPv4/netmask/description, ลบ IP และเปิด/ปิด interface | ปุ่มเปิด/ปิดไม่บังคับให้ interface มี IP; ต้องตรวจผลกับอุปกรณ์หลัง Apply |
| Loopback | เพิ่มหรือแก้ Loopback ผ่านฟอร์มแยกในส่วน Interface | โค้ดมีแล้ว แต่หลักฐาน manual EVE ของ Phase 5 ยังไม่ปิด checkpoint |
| Switch L2/L3 | Access port/VLAN, VLAN, SVI และ routed port; ตรวจ capability ของอุปกรณ์ก่อนแสดง/ใช้คำสั่งเฉพาะ | แท็บ Routing ซ่อนสำหรับ Node ที่บันทึกเป็น Switch; การเปลี่ยน routed port กลับเป็น L2 คืนเพียง `switchport` ไม่คืนค่า L2 เดิมทั้งหมด |
| Routing | Static/default route, RIP, OSPF, EIGRP, BGP พร้อม flow เพิ่ม/แก้/ลบที่รองรับ | อ่านสถานะ routing จากอุปกรณ์; มุ่ง Cisco IOS IPv4 basic lab ไม่ใช่ policy ขั้นสูง |
| Show | สั่งรายการที่อนุญาต เช่น interface brief, route, protocol, neighbor, running-config | ไม่ใช่ช่องให้พิมพ์คำสั่งใดก็ได้; แสดง parsed data เมื่อรองรับ และ raw output เมื่อ parser ใช้ไม่ได้ |
| Preview → Apply | แสดง CLI ที่ backend สร้างจากข้อมูลฟอร์มก่อนส่งจริง; ต้องกด Apply แยก | Preview หมดอายุใน 5 นาที และ Apply ตรวจ operation/payload hash; ผลแต่ละคำสั่งบันทึกแยก |
| Save Config | มีปุ่ม Preview/Apply สำหรับ `write memory` | Apply อื่น ๆ ไม่บันทึก startup-config อัตโนมัติ |
| History | ดูประวัติคำสั่ง/ผลลัพธ์, ชื่อ Node ปัจจุบันหรือชื่อที่เก็บไว้ก่อนลบ, กรอง Node/สถานะ/ช่วงเวลา, เปลี่ยนหน้าและดูรายละเอียด | เวลาที่กรองใน UI เป็นเวลาท้องถิ่น; backend เก็บเวลา UTC และกรองก่อนแบ่งหน้า |

## จุดเด่นเชิงการออกแบบ

- แยกหน้าที่ชัด: React รับข้อมูลและแสดงสถานะ, FastAPI ตรวจสัญญาข้อมูล, Jinja2 สร้าง Cisco CLI, Netmiko ติดต่ออุปกรณ์, SQLite เก็บ Node/operation/history
- ฟอร์มส่ง **ข้อมูลที่มีชนิดชัดเจน** ไป backend; frontend ไม่ประกอบ Cisco CLI เอง จึงใช้ validation และ template เดียวกันก่อน Preview/Apply
- อ่าน configuration จริงก่อนเติมค่าฟอร์มหลายส่วน ลดการพิมพ์ interface/IP ซ้ำและช่วยให้เห็นค่าที่อุปกรณ์กำลังใช้
- มีผลทดสอบเชื่อมต่อเป็นรายขั้นและอัปเดตสถานะ Node เมื่อทดสอบใหม่ จึงแยกปัญหา Ping/port/login ได้
- ระหว่าง Apply มี lock ต่อ Node, ใช้ connection อายุสั้น และเก็บผลรายคำสั่ง; หากล้มเหลวบางส่วนจะแสดง partial failure แทนการอ้างว่าย้อนกลับอัตโนมัติ
- Credential ถูกเข้ารหัสด้วย Fernet ก่อนเก็บใน SQLite; response ไม่ส่งรหัสผ่านกลับ และมีการ redact ในประวัติ/ผลลัพธ์ที่เกี่ยวข้อง
- Scanner ใช้ได้โดยไม่ต้องเพิ่ม Node ก่อน แต่ยังมีทางกรอกเองสำหรับอุปกรณ์ที่สแกนไม่พบ
- ข้อความช่วยใช้งานใน Dashboard, Add Node, Node Detail และ History อธิบายที่มาของข้อมูลและผลของ Preview/Apply ชัดเจน โดยไม่เปลี่ยนสัญญา API หรือขั้นตอนตั้งค่า

## ขอบเขตและสถานะที่ต้องไม่เข้าใจผิด

- งานหลักถึง **Phase 4** อยู่ในโค้ดและ checklist; รายการ Loopback/Switch ของ **Phase 5** มี implementation/test แต่ `docs/TASKS.md` ยังรอหลักฐาน manual EVE สำหรับ Loopback, L2 access VLAN+SVI และ L3 routed port จึงยังไม่ถือว่าผ่าน checkpoint นั้น
- Connected หมายถึง **ผลตรวจล่าสุดผ่าน** ไม่ใช่ session ที่เชื่อมค้างตลอด หากอุปกรณ์ดับหลังการตรวจ สถานะจะเปลี่ยนเมื่อมีการตรวจครั้งถัดไป
- Scan เป็นการหา port SSH/Telnet ที่เปิดอยู่ ไม่ใช่ CDP/LLDP discovery และไม่สามารถตรวจ switch L2 ที่ไม่มี IP สำหรับบริหารจัดการ
- ยังไม่มี terminal สำหรับส่ง raw config CLI ใน UI; แท็บ CLI เป็น placeholder การตั้งค่าต้องผ่านฟอร์มและ Preview/Apply
- ไม่มี automatic rollback หรือ transaction บนอุปกรณ์ Cisco IOS; เมื่อ Apply หลายคำสั่งแล้วบางคำสั่งล้มเหลว ต้องตรวจ state จริงและแก้ไขต่อ
- การเปลี่ยนค่า running-config **ไม่เท่ากับ** การบันทึก startup-config; ใช้ Save Config เมื่อยืนยันแล้วว่าต้องการเก็บค่าหลัง reboot
- ไม่ควรตีความว่าเป็นระบบ production/multi-user: auth/roles, backup/diff/restore, advanced L2, ACL/NAT/AAA, IPv6 และการขยายระบบอยู่ใน backlog หรืออยู่นอกขอบเขตปัจจุบัน ดู [CONFIG_COVERAGE.md](CONFIG_COVERAGE.md) และ [TASKS.md](TASKS.md)
