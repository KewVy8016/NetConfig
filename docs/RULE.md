# NetConfig — กฎที่ห้ามละเมิด

เอกสารนี้ต้องอ่านร่วมกับ `../AGENTS.md` ก่อนเริ่มแก้โค้ดหรือ UI.

## 1. ขอบเขตและหลักความปลอดภัย

1. ใช้ Python 3.11+, FastAPI, Netmiko, Jinja2, Pydantic, SQLite, React/Vite/Tailwind,
   React Hook Form/Zod, TanStack Query และ Fernet ตามโจทย์. การเพิ่ม dependency ต้องมีเหตุผล
   และ test; ห้ามแทน stack ที่กำหนด.
2. EVE-NG เป็น network จริงในมุมโปรแกรม: ห้ามเรียก EVE API. Device identity คือ node ที่
   ผู้ใช้บันทึกไว้ พร้อม management endpoint และ credential ที่เข้ารหัส.
3. Browser ห้ามส่ง Cisco CLI ไปตั้งค่าโดยตรง. ทุก mutation ต้องผ่าน validate → render
   template → preview → explicit apply → detect error → audit/history.
4. ให้ backend ตรวจ input ซ้ำเสมอ; Zod เป็น UX layer ไม่ใช่ security boundary.
5. ใช้ allowlist command และ typed template variables. ห้าม string concatenation ด้วย input
   ของผู้ใช้เพื่อสร้าง CLI, ห้าม shell execution, และห้าม raw terminal เป็นทางลัดของ config form.
6. ค่า password/enable secret ต้องเข้ารหัสก่อนเขียน SQLite, ถูก decrypt เฉพาะช่วงเชื่อมต่อ,
   และ redact จาก API response, error, log, history, test และ UI. Fernet key มาจาก environment
   หรือ secret store เท่านั้น ไม่ commit `.env`/key.
7. SSH เป็นค่าเริ่มต้น. Telnet/Serial แสดงคำเตือนความเสี่ยง; Telnet ต้องไม่ส่ง secret ไปที่
   log. ไม่บันทึก config ด้วย `write memory` โดยอัตโนมัติ.
8. Netmiko blocking และไม่ thread-safe: เปิด connection ต่อ operation, รันใน FastAPI
   threadpool, กำหนด timeout, และ lock ต่อ node เพื่อห้าม mutation ซ้อนกัน. ต้อง disconnect
   ใน `finally`.
9. อย่าแสดง traceback, internal host detail หรือ secret ให้ผู้ใช้. แปลงเป็น error code,
   ข้อความไทย และ correlation ID; เก็บรายละเอียดแบบ redacted สำหรับ developer.
10. การลบ protocol/node, shutdown interface และ save config ต้องยืนยันก่อน apply.

## 2. ความถูกต้องของ Network Config

- IPv4 address, netmask, wildcard, network และ next-hop validate ด้วย `ipaddress`.
- UI รับ netmask ปกติ; backend คำนวณ wildcard สำหรับ OSPF/EIGRP และตรวจ network boundary.
- ตรวจ range: OSPF process 1–65535, area 0–4294967295, EIGRP AS 1–65535, BGP ASN ตาม
  IOS capability ที่ประกาศ. ห้าม silently clamp/แก้ค่าผู้ใช้.
- ก่อน apply ตรวจ duplicate/conflict ใน payload และอ่าน current configuration เมื่อต้องรู้
  context. ผลลัพธ์ CLI ที่มี `% Invalid input`, `% Incomplete command`, `% Ambiguous command`,
  `% Error`, หรือ error pattern ที่กำหนด ต้องเป็น failed command.
- ทุก config ที่สร้างต้องมี inverse/remove action ที่กำหนดชัด. การแก้ entry ให้ render
  remove ของค่าเก่าแล้ว add ค่าใหม่ หรือใช้ IOS syntax ที่ปลอดภัยตาม template.
- Apply แบบหลายคำสั่งต้องบันทึก per-command result; เมื่อบางคำสั่งล้มเหลวให้หยุด, รายงาน
  partial state และเสนอ recovery ที่ปลอดภัย. ห้ามอ้างว่า atomic หาก Cisco IOS ไม่ atomic.

## 3. โค้ด คุณภาพ และภาษา

- ทุกไฟล์มี header ภาษาไทย 1–2 บรรทัด. ทุก public Python function/class มี Thai docstring
  ระบุหน้าที่, parameters, return และ errors. ทุก Python function มี type hints.
- ชื่อไฟล์/ตัวแปร/ฟังก์ชัน/class เป็นอังกฤษ: Python `snake_case`, React `camelCase`/
  `PascalCase`. Comment อธิบาย “ทำไม” ไม่อธิบายสิ่งที่ชื่อโค้ดบอกอยู่แล้ว.
- ฟังก์ชันหนึ่งทำหนึ่งเรื่องและควรไม่เกินประมาณ 40 บรรทัด. แยก constant พร้อม comment
  เหตุผล. ห้ามมี commented-out code, TODO คลุมเครือ, dead code หรือ `any` ที่เลี่ยง type check.
- Jinja2 ทุกไฟล์ระบุตัวแปรที่ต้องการด้วย Thai header. React component ต้องมี comment Thai
  สั้น ๆ ระบุหน้าที่/props และอธิบาย side effect ที่ซับซ้อน.
- UI ต้องตรง Design: desktop-first, ไม่มี emoji, สถานะต้องเป็น color + icon + text,
  keyboard accessible, และมี loading/success/error/empty states.
- ก่อนแก้ UI ต้องอ่าน `Design/DESIGN.md` และ HTML reference ของหน้าที่เกี่ยวข้อง; หลังแก้
  ต้องทำ Design QA ตาม `AGENTS.md`. หาก Design กับ implementation ไม่ตรง ให้แก้ Design
  reference พร้อม decision ที่อนุมัติ หรือแก้ implementation กลับ ห้ามปล่อยให้ต่างกัน.

## 4. ข้อมูลและ Audit

- SQLite เก็บ node metadata, encrypted credentials, config operations และ immutable command
  history. `history` ต้องไม่แก้ผลลัพธ์เก่าและไม่เก็บ secret.
- Record mutation อย่างน้อย: id, correlation ID, time UTC, actor (เมื่อมี auth), node ID,
  operation type, preview hash, rendered commands ที่ redact แล้ว, result ต่อ command,
  overall outcome และ error code.
- Clear History ต้องกำหนด retention/สิทธิ์และยืนยัน; รุ่นแรกห้ามลบ audit ทั้งหมดจริง
  จนกว่าจะมี decision เรื่อง retention.

## 5. การทดสอบและการส่งมอบ

- Unit test renderer/validator/parser ทุก protocol, API test authorization/error mapping,
  และ fake Netmiko test timeout/CLI error/cleanup. ไม่พึ่ง EVE จริงเป็น test เดียว.
- ทดสอบ manual ตาม checkpoint กับ IOS image ที่ระบุ version. แยก test ที่ต้องใช้ serial
  adapter ออกชัดเจน.
- ก่อนส่ง: run formatter/linter/type check/test ที่โครงการกำหนด, ตรวจว่า secret ไม่อยู่ใน
  diff, และรายงานผลจริง. ห้ามปิด test หรือ weaken validation เพื่อให้ผ่าน.
