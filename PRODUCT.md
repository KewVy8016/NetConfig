# NetConfig — ข้อมูลผลิตภัณฑ์

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

นักศึกษาที่ตั้งค่าและตรวจสอบอุปกรณ์ Cisco IOS ในห้องปฏิบัติการเครือข่าย
ผู้ใช้ทำงานจาก Windows PC กับ EVE-NG หรืออุปกรณ์ที่เชื่อมต่อผ่าน USB Console
เป็นโปรเจกต์เรียน ไม่ใช่ระบบ production แบบหลายผู้ใช้

## Product Purpose

ช่วยเพิ่มอุปกรณ์ ตั้งค่าเครือข่าย และตรวจสอบผลโดยไม่ต้องเขียนคำสั่ง IOS เองทุกครั้ง
ผู้ใช้ยืนยันงานหลักสำหรับ UI ใหม่: **เพิ่ม Node → ตั้งค่า Interface/Routing → ตรวจผลและ History**
ความสำเร็จคือทำเส้นทางนี้ได้ชัดเจน มองเห็นสถานะจริง และค้นหาผลการทำงานย้อนหลังได้

## Positioning

แปลงข้อมูลจากฟอร์มเป็น Cisco IOS CLI ที่ฝั่ง backend ให้ตรวจ Preview ก่อน Apply
แล้วเก็บผลคำสั่งใน History พร้อมช่องทาง CLI แยกสำหรับงานที่ต้องใช้คำสั่งโดยตรง

## Operating Context

- ติดต่ออุปกรณ์ผ่าน SSH, Telnet หรือ Serial โดยไม่ใช้ EVE API
- การเชื่อมต่อเครือข่ายใช้ management IP; Serial ใช้พอร์ตที่ต่ออยู่กับเครื่อง backend
- ผู้ใช้เพิ่ม Node และทดสอบการเชื่อมต่อก่อนบันทึก จากนั้นเลือก Interface หรือ Routing
- การตรวจผลใช้สถานะการเชื่อมต่อ, Show commands และ Command History
- งานออกแบบต้องคงพฤติกรรมตาม `Design/DESIGN.md` เว้นแต่ผู้ใช้อนุมัติให้เปลี่ยน

## Capabilities and Constraints

- Node management, network scan และการเลือก USB/Serial port
- Interface IPv4 และการเปิด/ปิดพอร์ต; Loopback และ Switch L2/L3 ตาม capability อุปกรณ์
- Static/default route, RIP, OSPF, EIGRP และ BGP ตามขอบเขตที่บันทึกในเอกสารโครงการ
- Show commands, command preview, explicit apply, History และ CLI terminal
- สถานะที่แสดงต้องแยกจากผลทดสอบครั้งเก่า ไม่อ้างว่ากำลังเชื่อมต่อเมื่อยังไม่ทราบผลล่าสุด
- คงขั้นตอน Preview → ยืนยัน Apply → ผลรายคำสั่ง → History
- ไม่บันทึก startup config อัตโนมัติ; Save Config เป็นการกระทำแยกที่ผู้ใช้เลือก
- UI redesign ไม่เปลี่ยน API, database หรือเทคโนโลยีโดยไม่จำเป็น
- รายละเอียดความสามารถและข้อจำกัดอ้างอิง `docs/CONFIG_COVERAGE.md` และ `docs/TASKS.md`

## Brand Commitments

ชื่อผลิตภัณฑ์ NetConfig ข้อความอธิบายและ error ใช้ภาษาไทยที่ตรงไปตรงมา
ชื่ออุปกรณ์, Interface, protocol และคำสั่งใช้ศัพท์จริงของอุปกรณ์
ผู้ใช้ขอ UI ที่ดูเป็นเครื่องมือใช้งานมืออาชีพ ไม่ให้หน้าตาบดบังงานหลัก
ผู้ใช้เลือกแนวทาง Device Index และขอไม่แสดงแผงสอนขั้นตอนใต้รายการ Node

## Evidence on Hand

มีโค้ด frontend/backend, Design HTML และเอกสาร workflow ใน repository
มีข้อมูล Node ของห้องทดลองในแอปจริง; ห้ามสร้างตัวเลขความสำเร็จหรือผลตรวจอุปกรณ์ขึ้นเอง
ข้อมูลสาธิตที่ใช้เพื่อออกแบบต้องระบุว่าเป็นตัวอย่างและไม่ปะปนกับสถานะจริง

## Product Principles

1. งานตั้งค่า Interface/Routing เป็นทางหลัก; CLI เป็นทางเลือกเสริม
2. ให้เห็นว่าเลือกอุปกรณ์ใด จะเปลี่ยนอะไร และผลเป็นอย่างไร
3. ความล้มเหลวต้องบอกขั้นตอนและทางแก้ ไม่ใช้เพียงข้อความ Error
4. รักษาฟังก์ชันเดิมและใช้การตรวจเฉพาะส่วนที่จำเป็นตามความต้องการประหยัด Token

## Accessibility & Inclusion

ตาม design contract: สถานะต้องมีสีร่วมกับ icon และข้อความ
รองรับ keyboard Tab/Enter/Escape, focus ที่เห็นได้ และหน้าจอ desktop/tablet
