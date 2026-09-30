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
| ADR-027 | Interface table มี Admin State toggle แบบ preview ก่อน apply | Toggle ท้ายแต่ละแถวใช้ intent แบบ typed ที่มีเพียง interface name และ admin state จึงใช้ได้ทั้งพอร์ตที่มีและไม่มี IPv4. การคลิกสร้าง preview `shutdown`/`no shutdown` เท่านั้น; Apply ยังต้องกดยืนยันใน preview dialog และการปิดพอร์ตต้องมี confirmation. owner: frontend/backend; อนุมัติ 2026-09-23 |
| ADR-028 | Switch ไม่แสดง Routing และ config profile รองเปิดด้วย dialog | Node ที่บันทึกเป็น Switch แสดงเฉพาะ Interfaces, Show และ CLI; งาน Loopback/L2 Access/L3 Routed/VLAN-SVI เปิดจาก Additional Configuration dialog ขณะที่ Configure Interface หลักยัง inline. ทุก dialog ยังส่ง typed intent เข้า preview เดิมและไม่ Apply อัตโนมัติ. owner: frontend/design; อนุมัติ 2026-09-23 |
| ADR-029 | ย้าย Network Scanner ใน Add Node เป็น dialog | ตามคำขอผู้ใช้: Scan Network เปิดเป็น centered dialog เฉพาะ SSH/Telnet เพื่อลดความรกของ Protocol form. ผล Use SSH/Telnet เติม transport/host/port แล้วปิด dialog; ไม่มี login หรือการสร้าง Node ระหว่าง scan. owner: frontend/design; อนุมัติ 2026-09-23 |
| ADR-030 | History แบ่งหน้าและบันทึก Show แบบ append-only | ตามคำขอให้ History สมบูรณ์: `GET /history` รับ limit/offset และส่งยอดรวมใน `X-Total-Count`, `GET /history/nodes` ให้ตัวเลือก Node ไม่ขึ้นกับตัวกรอง; บันทึกคำสั่ง Show ที่เรียกจาก UI ทั้ง success/failure พร้อม correlation ID และ output ที่ redact. ไม่เพิ่ม Clear/Delete; retention/export ยังคง OD-007. owner: backend/frontend/design; อนุมัติ 2026-09-26 |
| ADR-031 | ปรับ History ให้อ่านและกรองง่ายขึ้น | ตามคำขอผู้ใช้: ย่อ toolbar ตัวกรองให้วางแถวเดียวบน desktop, แสดงชื่อ action ภาษาไทยพร้อม type เดิม, แยกวัน/เวลา, แสดงผลทีละ 10 รายการ, ใช้ expandable cards บน tablet และย้าย audit IDs ไป disclosure รอง. ไม่เปลี่ยนข้อมูล/ลำดับ audit หรือ API. owner: frontend/design; อนุมัติ 2026-09-26 |
| ADR-032 | ชื่อ Node ใน History อิงรายการ Node ปัจจุบัน | ตัวกรองรวมทุก Node ปัจจุบันแม้ยังไม่มี history; ชื่อในแถวใช้ hostname ล่าสุดจากรายการ Node. Node ที่ลบแล้วแต่มี audit ยังคงเลือกได้โดยติดป้าย “ลบแล้ว” และแถวใช้ hostname snapshot เดิม. จำกัดความกว้างเนื้อหา 896px และกำหนดสัดส่วนคอลัมน์เพื่อลดตารางที่ยืดผิดสัดส่วน. ไม่เปลี่ยนหน้า Nodes หรือ backend API. owner: frontend/design; อนุมัติ 2026-09-26 |
| ADR-033 | History กรองตามช่วงวันเวลาแบบ server-side | UI รับเวลาท้องถิ่นตั้งแต่/ถึงแบบนาที, ส่ง `created_from` และ `created_before` เป็น UTC โดยขอบเขตบน exclusive (ถัดจากนาทีที่เลือก). Backend ตรวจเขตเวลาและลำดับช่วง แล้วกรองก่อนนับและแบ่งหน้า. ปุ่ม pagination แบบมีกรอบและคอลัมน์รายละเอียดจัดกึ่งกลาง. owner: backend/frontend/design; อนุมัติ 2026-09-26 |
| ADR-034 | Add Node แสดงพอร์ต USB Console ที่เครื่อง backend ตรวจพบ | ตามคำขอผู้ใช้: เมื่อเลือก Serial ให้ backend อ่าน COM/tty ผ่าน pySerial โดยไม่เปิดพอร์ต; UI แสดงชื่อพอร์ต+คำอธิบาย, เรียง USB ก่อน, รีเฟรชอัตโนมัติขณะเปิดขั้น Protocol และมีปุ่มรีเฟรช/กรอกเอง. ไม่ใช่พอร์ตของเครื่องที่เปิด browser หาก backend อยู่คนละเครื่อง. Test & Save เดิมยังบังคับ; owner: backend/frontend/design; อนุมัติ 2026-09-29 |
| ADR-035 | ปรับข้อความช่วยใช้งานโดยไม่เปลี่ยน workflow | ตามคำขอผู้ใช้: ให้แต่ละหน้าบอกหน้าที่ ข้อมูลที่แสดง ผลของการกดปุ่ม และขั้นตอนถัดไปด้วยภาษาไทยที่กระชับ; คงชื่อ Cisco/Protocol/Preview/Apply เพื่อให้ตรงกับการทำงานจริง. Dashboard/Node Detail อธิบายว่าสถานะเป็นผลตรวจล่าสุด, Add Node แยกการทดสอบ Serial จาก SSH/Telnet, History เป็นบันทึกย้อนหลัง, และ Preview ไม่ส่งคำสั่งจนกด Apply. ไม่เปลี่ยน API หรือการสร้างคำสั่ง; owner: frontend/design/docs; อนุมัติ 2026-09-29 |
| ADR-036 | ตรวจ privilege ก่อนสรุปว่าขาด Enable Secret | เมื่ออยู่ user EXEC ให้ลอง `enable` ก่อน เพราะ console หลายเครื่องไม่ถามรหัส; แจ้ง `ENABLE_SECRET_REQUIRED` เฉพาะเมื่ออุปกรณ์ถามและไม่มี secret. Routing อ่าน running-config ได้โดยไม่ขึ้นกับ IP interface; เมื่ออ่านไม่สำเร็จ UI แสดง “อ่านไม่ได้” ไม่ใช่ “Off”. แทนพฤติกรรมที่เข้มเกินไปใน ADR-015; owner: backend/frontend; อนุมัติจากคำขอผู้ใช้ 2026-09-29 |
| ADR-037 | เปิด CLI session สำหรับแล็บแบบผู้ใช้เครื่องเดียว | ตามคำขอผู้ใช้แทน ADR-023/OD-004: CLI แยกจาก typed Preview/Apply, เปิด WebSocket session ชั่วคราวและส่งคำสั่งทีละบรรทัดทันที; มีคำเตือน, ปุ่ม disconnect, idle timeout, lock ต่อ Node และ History ต่อคำสั่งโดยไม่เก็บข้อความคำสั่ง/output ที่อาจมีรหัส. ยังไม่มี web authentication ตามขอบเขตแล็บที่ผู้ใช้กำหนด; ห้ามเปิดบริการให้ผู้ใช้อื่นบนเครือข่าย. owner: backend/frontend/design; อนุมัติจากคำขอผู้ใช้ 2026-09-29 |
| ADR-038 | Delete Node เก็บ audit เดิม | เพิ่มปุ่มลบใน Dashboard และ Node Detail โดยยืนยันชื่อก่อนเรียก DELETE; ลบ metadata/credential และ pending operations ของ Node แต่ไม่เปลี่ยน config อุปกรณ์หรือ History ที่บันทึกไว้. owner: backend/frontend/design; อนุมัติจากคำขอผู้ใช้ 2026-09-29 |
| ADR-039 | Routing state ไม่บังคับ Router ID ที่ยังไม่ตั้ง | แยก read-state schema จาก config input: process/network/neighbor ที่มีอยู่ใน running-config ต้องแสดงได้แม้ interface ยังไม่มี IP และ router ID ไม่ได้กำหนด; คืน `router_id: null` ตามจริง ไม่เติมค่าเทียม. ฟอร์มเพิ่ม/แก้ยังต้องรับ Router ID ที่ถูกต้องก่อน Preview; การลบ resource ใช้ snapshot ที่อ่านได้. owner: backend/frontend/design; อนุมัติจากคำขอผู้ใช้ 2026-09-29 |
| ADR-040 | หน้า CLI เป็น workspace เดียวแบบ device console | ตามคำขอปรับ UI: รวม output กับ prompt/input ใน terminal สีเข้มกรอบเดียว, metadata/session/Copy/Clear/Disconnect อยู่แถบบนแบบกระชับ, คำเตือนเป็นแถบบาง, แสดง disconnected/error เมื่อ socket ใช้งานไม่ได้ ไม่ปล่อยให้ Send เงียบ; ไม่แสดง uptime ที่ไม่ได้อ่านจากอุปกรณ์หรือ decoration เลียนแบบ desktop window. คง WebSocket contract, audit และ typed config flow เดิม; owner: frontend/design; อนุมัติจากคำขอผู้ใช้ 2026-09-29 |
| ADR-041 | แยก page navigation จาก API ใน Vite proxy | หน้า React และ API ใช้ `/nodes`/`/history` ร่วมกัน; GET ที่รับ `text/html` และไม่ใช่ WebSocket ให้โหลด `index.html` เพื่อให้ refresh/deep link ทำงาน ส่วน request API และ WebSocket ยังคง proxy ไป backend โดยไม่เปลี่ยน URL/schema. owner: frontend/docs; แก้ตามปัญหาที่ผู้ใช้รายงาน 2026-09-30 |

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
| OD-004 (resolved) | terminal อนุญาตในรุ่นส่งงานหรือไม่ | เปิดใช้เฉพาะแล็บผู้ใช้เครื่องเดียวตาม ADR-037; หากใช้หลายผู้ใช้ต้องตัดสินเรื่อง auth/roles ใหม่ |
| OD-005 | scanner ปลอดภัยแค่ไหน | จำกัด subnet size/rate/concurrency, opt-in, และไม่มี port scan เกิน SSH/Telnet |
| OD-006 | อุปกรณ์/IOS ที่รับรอง | ระบุ exact EVE image และ hardware/IOS versions ใน README/test matrix |
| OD-007 | history retention/export | กำหนด duration, redaction, access control และ backup ก่อนเปิด Clear History |
| OD-008 (resolved) | เมื่อเปลี่ยน L2 switchport เป็น L3 routed port ต้องการ inverse/restore ระดับใด | เลือกข้อ (ก) ผ่าน ADR-026: คืน L2 พื้นฐานเท่านั้น ไม่คืน VLAN/trunk/description/admin state เดิม |
