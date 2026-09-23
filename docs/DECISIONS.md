# NetConfig — ข้อตกลงและ Architectural Decisions

ให้ใช้ร่วมกับ `../AGENTS.md` และ `RULE.md`.

เอกสารนี้บันทึกสิ่งที่ตัดสินใจแล้วเพื่อให้หลายเอเจนต์ทำงานต่อกันได้ ถ้าต้องเปลี่ยน decision
ให้เพิ่มรายการใหม่ (อย่าแก้ประวัติเดิม) พร้อมเหตุผล, migration, owner และวันที่อนุมัติ.

## ตัดสินใจแล้ว

| ID | การตัดสินใจ | เหตุผล/ผลกระทบ |
|---|---|---|
| ADR-001 | ไม่ใช้ EVE API | ระบบใช้ IP + credential เดียวกับอุปกรณ์จริง จึง portable ระหว่าง EVE และ hardware |
| ADR-002 | รองรับ SSH, Telnet, Serial ด้วย Netmiko | ครบโจทย์; SSH เป็น default, Telnet/Serial เป็น compatibility path |
| ADR-003 | Server เป็น command authority | Browser ส่ง typed intent ไม่ส่ง config CLI; Jinja2 renderer เป็นจุดเดียวที่สร้างคำสั่ง |
| ADR-004 | Preview กับ Apply แยก operation | ผู้ใช้เห็นคำสั่งก่อนส่ง และลดความเสี่ยง apply จาก stale/เปลี่ยน form แล้ว |
| ADR-005 | Netmiko connection อายุสั้นและ lock ต่อ node | ลด race condition/connection leak เพราะ Netmiko blocking และไม่ thread-safe |
| ADR-006 | SQLite + Fernet สำหรับรุ่น Assignment | ติดตั้งง่าย; secret เข้ารหัส at rest แต่ key management ยังเป็น deployment responsibility |
| ADR-007 | `write memory` เป็น action แยก | ป้องกันการบันทึก config ที่ผู้ใช้ยังไม่ยืนยัน และตรงโจทย์ |
| ADR-008 | IPv4 Cisco IOS routing คือ scope core | Assignment ครอบคลุม interface, static/default, RIP, OSPF, EIGRP, BGP; advanced/IPv6 เป็น backlog |
| ADR-009 | Command history เป็น audit append-only | ต้องตามรอย preview/apply/error ได้; ปุ่ม clear UI ห้ามทำลาย audit โดยไม่มี retention policy |
| ADR-010 | Design HTML คือ visual/interaction reference ไม่ใช่ production code | ต้อง reimplement เป็น React components; ห้ามยก JavaScript mock data ไป production |
| ADR-011 | ทดสอบ connection ก่อนบันทึก Node | Add Node ต้องเรียก draft test ก่อนเขียน SQLite; หาก Ping/Port/Login/Hostname ไม่ผ่าน ให้แสดงผลและไม่สร้าง Node เพื่อป้องกันรายการ unreachable ค้างในระบบ; owner: backend/frontend; อนุมัติ 2026-09-22 |
| ADR-012 | Telnet รองรับ password-only login | IOS VTY บางแบบถามเฉพาะ password; อนุญาต username ว่างเฉพาะ Telnet และส่งค่าว่างให้ Netmiko ซึ่งรองรับ password-only ส่วน SSH/Serial ยังบังคับ username; owner: backend/frontend; อนุมัติ 2026-09-22 |
| ADR-013 | Serial credential เป็น optional | Console connection บางอุปกรณ์เปิดเข้าสู่ IOS prompt โดยไม่ถาม username/password; อนุญาตค่าว่างเฉพาะ Serial และส่งให้ Netmiko serial login ส่วน SSH ยังคงบังคับ credential; owner: backend/frontend; อนุมัติ 2026-09-22 |
| ADR-014 | Node ที่ผ่าน Test & Save เริ่มต้นเป็น Connected | ผล pre-save test คือ health evidence ล่าสุดของ Node; เมื่อบันทึกสำเร็จต้อง persist `connected` ทันที และ Reconnect บน Node Detail ต้องอัปเดตเป็น `connected`/`unreachable` ตามผลล่าสุด; owner: backend/frontend; อนุมัติ 2026-09-22 |
| ADR-015 | Show ไม่บังคับ enable; config mutation ต้องมี privilege | Show allowlist ทำงานจาก user EXEC เพื่อรองรับอุปกรณ์ที่มี enable secret แยก ส่วน Apply ต้องตรวจ privileged EXEC และคืน `ENABLE_SECRET_REQUIRED` เมื่อไม่มี secret แทนการค้างจน timeout; owner: backend; อนุมัติ 2026-09-22 |
| ADR-016 | Interface ต้องเลือกจาก inventory ของอุปกรณ์ | หน้า Interfaces โหลด `show ip interface brief` อัตโนมัติและใช้ select แทน free text; loading/error/empty หรือรายการ stale ต้องปิด Preview เพื่อป้องกันพิมพ์ผิดและส่ง config ไป interface ที่ไม่มีอยู่; owner: frontend; อนุมัติ 2026-09-22 |
| ADR-017 | เลือก Interface แล้ว prefill จาก actual state | Backend สร้าง `show interfaces <validated-name>` เองและ parse IP/prefix/description/admin state; frontend ห้ามสร้าง CLI หรือเดาค่าปัจจุบัน และปิด Preview ระหว่างโหลด; owner: backend/frontend; อนุมัติ 2026-09-22 |
| ADR-018 | Pin Paramiko 3.x สำหรับ IOSv legacy SSH | Netmiko 4.3 บน Paramiko 5 ไม่สามารถ negotiate legacy SSH algorithms ของ IOSv lab image ที่ใช้อยู่ แม้ Ping/TCP 22 ผ่าน; pin `>=3.4,<4.0` เฉพาะ compatibility path และควรอัปเกรด IOS/SSH policy ก่อนใช้ production; owner: backend; อนุมัติ 2026-09-22 |
| ADR-019 | Actual Static Route อ่านจาก privileged running-config | `show ip route` แสดงเฉพาะ route ที่ถูกติดตั้งและรูปแบบ classful อาจไม่คืน mask ต่อบรรทัด จึงไม่พอสำหรับสร้าง inverse command ที่แน่นอน; backend ต้องเข้า enable เฉพาะคำสั่ง read-only ที่จำเป็น, อ่าน running-config ฝั่ง server และคืนเฉพาะ `ip route` แบบ typed contract ที่ parser ยืนยันได้. Decision นี้เพิ่มข้อยกเว้นแบบเจาะจงให้ ADR-015; owner: backend; อนุมัติ 2026-09-22 |
| ADR-020 | RIP ใช้ major network boundary และบังคับ `no auto-summary` | IOS `router rip` ใช้คำสั่ง `network` แบบ classful major network; backend จึงปฏิเสธ subnet ที่ IOS จะ normalize เงียบ ๆ และให้ข้อความ boundary ที่ถูกต้อง. ทุก add/update ตั้ง version 1/2 แบบ explicit และ `no auto-summary`; actual state อ่านจาก privileged running-config ก่อน edit/remove; owner: backend/frontend; อนุมัติ 2026-09-22 |
| ADR-021 | Node status มี heartbeat ทุก 30 วินาทีบน Dashboard และ Node Detail | ค่า `nodes.status` เป็นผลตรวจครั้งล่าสุด ไม่ใช่ live socket; frontend จึงเรียก `POST /nodes/{id}/test` แบบ background ทุก 30 วินาทีขณะหน้านั้นเปิดอยู่ และแสดง Connected/Unreachable/Checking/Unknown จากผลล่าสุด. ไม่ทำ global backend polling เพื่อไม่สร้าง connection ไปทุกอุปกรณ์ตลอดเวลา; owner: frontend; อนุมัติ 2026-09-22 |
| ADR-022 | EIGRP ใช้ AS เดียวต่อ workflow และตั้ง `no auto-summary` เสมอ | Cisco IOS จะมี EIGRP process เดียวต่อ address family ใน scope นี้; backend อ่าน running-config และปฏิเสธ AS อื่นหรือ network ซ้ำก่อน preview. ทุก add/update ตั้ง router-id และ `no auto-summary` แบบ explicit; owner: backend/frontend; อนุมัติ 2026-09-22 |
| ADR-023 | ปิด raw CLI terminal ในรุ่น Assignment | Configuration ทุกชนิดใช้ typed form → preview → apply → history เท่านั้น; tab CLI แสดงข้อความว่าไม่เปิดใช้ เพื่อไม่เพิ่ม workflow นอก scope การสาธิต. owner: frontend; อนุมัติ 2026-09-22 |
| ADR-024 | Loopback เป็น resource แยกจาก physical interface inventory | `show ip interface brief` บอกได้เฉพาะ interface ที่มีอยู่แล้ว จึงห้ามใช้ select เดิมเพื่อสร้าง Loopback ใหม่. ผู้ใช้ระบุหมายเลข Loopback ผ่าน typed form; Create/Remove ต้อง preview ก่อน apply, การลบต้องมี confirmation, และไม่มี `write memory` อัตโนมัติ. owner: backend/frontend; อนุมัติ 2026-09-23 |
| ADR-025 | แสดง Switchport/L2 controls เฉพาะ node ที่บันทึกเป็น Switch | ลดข้อความที่ไม่เกี่ยวกับ Router ตาม UX ที่ผู้ใช้กำหนด; เป็นเพียง UI gate. Backend ยังอ่าน capability จริงก่อน preview เสมอ จึงไม่เดาบทบาทอุปกรณ์จากชื่อ node. owner: frontend/backend; อนุมัติ 2026-09-23 |
| ADR-026 | Restore L3 routed port คืนเพียง L2 switchport พื้นฐาน | ตามตัวเลือก 1 ที่ผู้ใช้อนุมัติ: inverse render `no ip address` แล้ว `switchport`; ไม่ snapshot และไม่คืน access VLAN, trunk, description หรือ admin state เดิม. UI ต้องเตือนและขอ confirmation ก่อน Apply ทุกครั้ง. owner: backend/frontend; อนุมัติ 2026-09-23 |
| ADR-027 | Interface table มี Admin State toggle แบบ preview ก่อน apply | Toggle ท้ายแต่ละแถวใช้ intent แบบ typed ที่มีเพียง interface name และ admin state จึงใช้ได้ทั้งพอร์ตที่มีและไม่มี IPv4. การคลิกสร้าง preview `shutdown`/`no shutdown` เท่านั้น; Apply ยังต้องกดยืนยันใน drawer และการปิดพอร์ตต้องมี confirmation. owner: frontend/backend; อนุมัติ 2026-09-23 |
| ADR-028 | Switch ไม่แสดง Routing และ config profile รองเปิดด้วย dialog | Node ที่บันทึกเป็น Switch แสดงเฉพาะ Interfaces, Show และ CLI; งาน Loopback/L2 Access/L3 Routed/VLAN-SVI เปิดจาก Additional Configuration dialog ขณะที่ Configure Interface หลักยัง inline. ทุก dialog ยังส่ง typed intent เข้า preview เดิมและไม่ Apply อัตโนมัติ. owner: frontend/design; อนุมัติ 2026-09-23 |

## Contract การทำงานร่วมกัน

### ภาวะของ configuration operation

```
DRAFT → VALIDATED → PREVIEWED → APPLYING → SUCCEEDED
                                  └──────→ PARTIAL_FAILED / FAILED / EXPIRED
```

- `PREVIEWED` มี TTL สั้นและ payload hash. Apply รับได้เฉพาะ preview ที่ยัง valid.
- `APPLYING` lock node เดียว; show read-only policy ต้องไม่แทรก session mutation.
- `PARTIAL_FAILED` คือสถานะจริงเมื่อคำสั่งต้น ๆ สำเร็จแล้วคำสั่งหลังล้มเหลว; ต้องเก็บ output
  ทั้งหมดแบบ redact และแสดงว่าค่าใดอาจค้างอยู่บน device.

### ความเป็นเจ้าของข้อมูล

| ข้อมูล | Source of truth | หมายเหตุ |
|---|---|---|
| Node metadata/credential | SQLite | credential encrypted, response ห้ามคืน secret |
| Desired request/preview/history | SQLite | immutable operation record และ payload hash |
| Actual running configuration/status | Cisco device | DB cache ห้ามอ้างว่าเป็น actual config โดยไม่มีเวลาตรวจล่าสุด |
| UI cache | TanStack Query | invalidate หลัง apply/test/reconnect ไม่ใช่ source of truth |

### Minimum error contract

API คืน `{code, message_th, correlation_id, details?}`. `details` มีได้เฉพาะข้อมูลที่ปลอดภัย
เช่น field validation หรือ CLI output ที่ redact. กลุ่ม code อย่างน้อย: `VALIDATION_ERROR`,
`NODE_NOT_FOUND`, `CONNECTION_TIMEOUT`, `AUTH_FAILED`, `DEVICE_UNREACHABLE`, `CLI_REJECTED`,
`PREVIEW_EXPIRED`, `NODE_BUSY`, `PARTIAL_APPLY`.

## Open decisions ก่อน production/lab ใหญ่

| ID | คำถามที่ต้องตัดสิน | ตัวเลือกเริ่มต้นที่เสนอ |
|---|---|---|
| OD-001 | จะมี authentication/role ใดบ้าง | อย่างน้อย admin/operator/viewer ก่อนเปิดใช้นอกเครื่องส่วนตัว |
| OD-002 | Fernet key อยู่ที่ใดและหมุนอย่างไร | environment secret, fail startup หากไม่มี key, มี documented rotation |
| OD-003 | rollback ระดับใด | เริ่ม pre-change snapshot + manual restore preview; ไม่สัญญา auto rollback |
| OD-004 | terminal อนุญาตในรุ่นส่งงานหรือไม่ | ปิด default; ถ้าเปิดให้ admin only, explicit warning และ full audit |
| OD-005 | scanner ปลอดภัยแค่ไหน | จำกัด subnet size/rate/concurrency, opt-in, และไม่มี port scan เกิน SSH/Telnet |
| OD-006 | อุปกรณ์/IOS ที่รับรอง | ระบุ exact EVE image และ hardware/IOS versions ใน README/test matrix |
| OD-007 | history retention/export | กำหนด duration, redaction, access control และ backup ก่อนเปิด Clear History |
| OD-008 (resolved) | เมื่อเปลี่ยน L2 switchport เป็น L3 routed port ต้องการ inverse/restore ระดับใด | เลือกข้อ (ก) ผ่าน ADR-026: คืน L2 พื้นฐานเท่านั้น ไม่คืน VLAN/trunk/description/admin state เดิม |
