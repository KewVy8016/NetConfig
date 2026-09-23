# NetConfig — คู่มือปฏิบัติงานสำหรับเอเจนต์

เอกสารนี้คือคำสั่งปฏิบัติงานหลักของ repository นี้ เอเจนต์ทุกคนต้องอ่านจนจบ
ก่อนแก้โค้ด และต้องทำตามลำดับเอกสารด้านล่าง ห้ามเดาขอบเขตงานจาก mockup เพียงอย่างเดียว

## ลำดับอ้างอิงที่มีผลผูกพัน

1. `docs/RULE.md` — กฎที่ห้ามละเมิด
2. `docs/DECISIONS.md` — ข้อตกลงและ architectural decisions ที่ตัดสินใจแล้ว
3. `docs/CONFIG_COVERAGE.md` — ขอบเขตระบบ ช่องว่าง และลำดับความสำคัญ
4. `docs/TASKS.md` — แผนงานกลางและสถานะ checkpoint
5. `Design/DESIGN.md` และ HTML ใน `Design/` — ข้อกำหนด UI และ interaction
6. โจทย์ Assignment 2 — แหล่งจริงอยู่ในไฟล์ที่ผู้ใช้แนบ; หากเข้าถึงไม่ได้ ให้ถาม
   ห้ามประดิษฐ์ข้อกำหนดใหม่

เมื่อเอกสารขัดกัน ให้ยึด `docs/RULE.md` เรื่องความปลอดภัย, ยึด Assignment เรื่องฟังก์ชัน
และ stack, และยึด Design เรื่องหน้าตา/UX หากยังตัดสินไม่ได้ ให้หยุดและบันทึกคำถามใน
pull request หรือรายงานผู้ประสานงาน ไม่เปลี่ยน decision เอง

## Design Compliance Gate — ต้องผ่านทุกงานที่แตะ UI

`Design/` คือ design contract ไม่ใช่เพียงภาพตัวอย่าง. ก่อนเขียนหรือแก้ frontend ทุกครั้ง
เอเจนต์ต้องอ่าน `Design/DESIGN.md` และหน้าจอ HTML ที่สัมพันธ์กับงานจนจบ แล้วบันทึกใน
คำอธิบายงานว่าได้ตรวจไฟล์ใดและจะ implement element/flow ใด. ตัวอย่าง: งาน Add Node ต้อง
อ่านทั้ง `Design/add-node.html` และส่วน Add Node ใน `Design/DESIGN.md`; งาน routing ต้องอ่าน
`Design/node-detail.html` และ Routing Tab specification.

ห้ามเปลี่ยนเองโดยไม่มีอนุมัติ: information architecture, tab/step flow, label สำคัญ,
interaction preview-before-apply, confirmation ที่ Design ระบุ, color token, typography,
spacing system, status semantics, หรือ responsive behavior. ห้ามใช้ mock HTML/JavaScript
เป็น production implementation; ต้องแปลงเป็น React โดยรักษาผลลัพธ์เชิงภาพและพฤติกรรม.

หาก requirement ใหม่บังคับให้ Design เปลี่ยน ให้หยุดก่อน implement, เสนอผลกระทบและรอ
การตัดสินใจ. เมื่อได้รับอนุมัติ ให้แก้ `Design/DESIGN.md` และ HTML reference ที่เกี่ยวข้อง
**ก่อนหรือพร้อมกับ** React implementation, ระบุ decision ใน `docs/DECISIONS.md`, และทำให้ทุก
หน้าจอ/ข้อความที่เกี่ยวข้องสอดคล้องกัน. ห้ามให้ production UI เปลี่ยนแต่ Design ค้าง.

ก่อนปิดงาน UI ต้องทำ Design QA: เปรียบเทียบกับ reference ที่ 1280px+ และ tablet 768–1024px,
ทดสอบ loading/success/error/empty states, keyboard Tab/Enter/Escape, และยืนยันว่า status
สื่อด้วย color + icon + text. แนบผลตรวจหรือภาพหลักฐานเมื่อ workflow รองรับ.

## เป้าหมายและขอบเขตปัจจุบัน

NetConfig คือ Web UI สำหรับตั้งค่า Cisco IOS IPv4 ผ่าน SSH, Telnet และ Serial โดยมอง
EVE-NG เป็นเครือข่ายจริง: โปรแกรมเชื่อมผ่าน management IP และ credential เท่านั้น
ไม่ใช้ EVE API. งานบังคับในรุ่นนี้คือ Node management, interface IPv4, static/default
route, RIP, OSPF, EIGRP, BGP, show commands, command preview, encrypted credential และ
command history. รายการที่อยู่นอกขอบเขตอยู่ใน `CONFIG_COVERAGE.md`.

## วิธีทำงานที่บังคับ

1. เริ่มจาก phase ที่ยังไม่ผ่านเท่านั้น: Phase 1 → 2 → 3 (ทีละ protocol) → 4.
   ห้ามสร้าง UI หรือ API ของ phase ถัดไปก่อน checkpoint ของ phase ปัจจุบันผ่าน.
2. ก่อนเขียน ให้ระบุไฟล์ที่จะเปลี่ยน, input/output contract, validation, error case,
   test และผลกระทบต่อ Design. งานหนึ่งต้องมีเจ้าของและขอบเขตเล็กพอตรวจได้.
3. ใช้ vertical slice: Pydantic schema → Jinja2 template → service → API → React form →
   test. ห้ามให้ frontend สร้าง Cisco CLI เอง หรือข้าม validation ไปเรียก device.
4. อ่านสถานะปัจจุบันก่อนแก้และรักษาแก้ไขเดิมของผู้อื่น. ห้าม reset, checkout ทับ,
   ลบไฟล์ หรือ format ทั้ง repository โดยไม่ได้รับอนุญาตชัดเจน.
5. หลังแก้ ให้รัน test/lint/type check ที่เกี่ยวข้อง; ระบุคำสั่งและผลจริง. ถ้าทดสอบกับ
   device จริงไม่ได้ ให้เพิ่ม unit/integration fake และรายงานสิ่งที่ยังต้องทดสอบ.
6. จบงานด้วย: สิ่งที่เปลี่ยน, contract ที่เพิ่ม/เปลี่ยน, test result, ความเสี่ยง,
   และ checkpoint ที่ผ่านหรือยังไม่ผ่าน. อย่าอ้างว่า complete หากยังไม่ผ่าน checkpoint.

## สถาปัตยกรรมและขอบเขตไฟล์

```
backend/
  main.py                 # app wiring, lifecycle, exception handlers
  models.py               # DB entities และ Pydantic request/response schemas
  routers/                # HTTP/WebSocket boundary; ไม่มี CLI และ business logic
  services/               # connection, renderer, scanner, parser, history
  templates/              # Cisco IOS command templates; ไม่มี user input ดิบประกอบคำสั่ง
  tests/                  # unit, API integration, fixture สำหรับ fake device
frontend/
  src/pages/              # Nodes, AddNode, NodeDetail, History
  src/components/         # forms, preview drawer, show panel, shared UI
  src/lib/                # API client, validation schema, formatters
docs/                     # เอกสารเพิ่มได้ แต่ห้ามย้ายเอกสาร root โดยพลการ
```

หากโครงสร้างจริงต่างจากนี้ ให้ค่อย ๆ ย้ายผ่านงานเฉพาะกิจพร้อม test; อย่าปะปน migration
ใหญ่กับ feature ใหม่. Router ทำเพียง authentication/authorization, schema conversion
และเรียก service. Service เป็นเจ้าของ transaction และ error domain. Template เป็นเจ้าของ
รูปแบบ CLI. React เป็นเจ้าของ UX state เท่านั้น.

## สัญญา API ขั้นต่ำ

- `POST /nodes` บันทึก node หลัง schema validation; response ห้ามมี password/enable secret.
- `POST /nodes/{id}/test` รายงานแต่ละขั้น Ping, port, login, hostname พร้อม status/message.
- คำขอ preview ต้อง render CLI จาก typed payload และคืน `operation_id`, commands และ
  validation warnings โดย **ยังไม่** ส่งอุปกรณ์.
- คำขอ apply ต้องอ้าง `operation_id` ของ preview ที่ยังไม่หมดอายุและ payload hash ต้องตรง;
  service ส่งเฉพาะ CLI ที่ renderer อนุญาต แล้วบันทึกผลราย command ลง history.
- API ที่เปลี่ยน config ทุกตัวต้องมี correlation ID, node ID, command type และ audit record.
- Show เป็น allowlist; raw output ได้ แต่ parser failure ต้องคืน raw output อย่างปลอดภัย.

ห้ามเปิด endpoint รับ `commands: string[]` จาก browser สำหรับ config. CLI terminal เป็น
ฟีเจอร์เสริมที่ต้องแยกจาก workflow configuration, มีคำเตือนและ audit เสมอ.

## Definition of Done ต่อหนึ่งงาน

- สอดคล้องกับ scope/decision และ UI ใน Design
- validation อยู่ทั้ง frontend (เพื่อ UX) และ backend (เป็น source of truth)
- input ที่ไม่ถูกต้อง, credential ผิด, timeout, CLI error และ device disconnect มีผลลัพธ์
  ที่ผู้ใช้เข้าใจได้ โดยไม่เผย secret/traceback
- มี test ที่ยืนยัน happy path และอย่างน้อยหนึ่ง failure path
- ไม่มี plaintext secret ใน DB, response, log, test fixture หรือ screenshot
- มี Thai file header, Thai public docstring และ type hints ตาม `RULE.md`
- ถ้าเป็น config mutation: preview → explicit apply → per-command result → history ครบ
- ไม่มีการ `write memory` อัตโนมัติ และ destructive action มี confirmation

## Checkpoint ที่ห้ามข้าม

| Phase | ผลลัพธ์บังคับ | หลักฐานขั้นต่ำ |
|---|---|---|
| 1 | เพิ่ม node และ test connection ผ่าน SSH/Telnet/Serial | `show ip interface brief` จาก fixture/device และ API test |
| 2 | ตั้ง IPv4/shutdown และ Show | router สองตัว ping กันได้ หรือ integration evidence เทียบเท่า |
| 3a | Static/default route | route ปรากฏใน `show ip route` และลบกลับได้ |
| 3b–e | RIP → OSPF → EIGRP → BGP ทีละตัว | neighbor/route show ที่ตรง protocol และ remove ได้ |
| 4 | scanner, preview, history และ optional terminal/bootstrap | security regression และ UX acceptance ตาม Design |

## กฎการประสานงาน

- งานเดียวแก้ส่วนเดียว: แจ้งเจ้าของก่อนแตะ shared contract (`models`, API client, routes,
  design tokens). ถ้าต้องเปลี่ยน ให้แก้ contract และ consumer ในงานเดียวกัน.
- ห้ามเปลี่ยนชื่อ, API shape, database schema หรือ technology ที่ตกลงไว้โดยไม่แก้
  `DECISIONS.md` และได้รับความเห็นชอบ.
- แยก commit ตามเจตนา: infrastructure, vertical feature, tests หรือ docs. ห้ามรวม
  refactor ที่ไม่เกี่ยวข้อง.
- เขียนข้อความ UI และ error เป็นภาษาไทยที่ตรงไปตรงมา; ชื่อโค้ดเป็นอังกฤษ.
- เมื่อพบ requirement ที่ไม่มี decision ให้เพิ่มเป็น "Open decision" ใน `DECISIONS.md`
  พร้อมตัวเลือกและผลกระทบ แทนการเลือกเอง.
