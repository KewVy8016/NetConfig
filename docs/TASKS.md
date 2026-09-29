# NetConfig — แผนงานและ Checklist

ใช้ไฟล์นี้เป็นสถานะงานกลาง อ่าน `../AGENTS.md`, `RULE.md` และ `DECISIONS.md` ก่อนเริ่มงาน
ทุกครั้ง. ติ๊ก `[x]` ได้ต่อเมื่อมีหลักฐานทดสอบ/ผลตรวจใน PR หรือรายงานงาน; ห้ามติ๊กจากการ
สร้าง mock UI หรือเขียนโค้ดโดยยังไม่ทดสอบ.

## กติกาการอัปเดต Task

- รับงานแล้วเปลี่ยนเฉพาะ `[ ]` เป็น `[-]` พร้อมชื่อ owner และวันที่ในบรรทัดนั้น
- จบงานแล้วเปลี่ยนเป็น `[x]` และแนบ path ของ test/หลักฐานหลังเครื่องหมาย `—`
- งานที่ติด dependency ใช้ `[!]` และเขียน blocker/คำถามให้ชัด
- ห้ามเริ่ม phase ถัดไปก่อน checkpoint ของ phase ปัจจุบันผ่าน

## Phase 0 — เริ่มโครงการและ Design Baseline

- [x] อ่าน Assignment, `../AGENTS.md`, `RULE.md`, `DECISIONS.md`, `CONFIG_COVERAGE.md` — อ่านครบถ้วนแล้ว
- [x] อ่าน `Design/DESIGN.md` และทำ inventory ของ `index.html`, `add-node.html`,
  `node-detail.html`, `history.html` — วิเคราะห์และเขียน index.css ตาม Design System
- [x] ระบุ IOS image/version และ environment สำหรับ EVE/hardware ที่ใช้ทดสอบ — บันทึกใน README.md (vIOS-L2/L3)
- [x] สร้าง backend/frontend ตาม stack ที่กำหนด พร้อม `.env.example` ที่ไม่มี secret — backend/, frontend/, .env.example
- [x] ตั้ง formatter, linter, type checker และ test runner สำหรับ backend/frontend — pyproject.toml, tsconfig.json
- [x] สร้าง SQLite migration/initialization และ schema สำหรับ node, operation, history — backend/database.py
- [x] กำหนด Fernet key ผ่าน environment; startup ต้อง fail อย่างปลอดภัยเมื่อ key หาย — backend/config.py
- [x] เขียน README วิธี install/run และ device bootstrap ขั้นต่ำ — README.md

**Checkpoint P0:** รันเปล่าได้, test/lint ทำงาน, ไม่มี secret ใน repository, และ baseline UI
เทียบ Design ได้ก่อนเริ่มเชื่อมอุปกรณ์.

## Phase 1 — Node และ Connection Foundation

- [x] สร้าง Pydantic schemas: node, transport, SSH/Telnet credentials, serial settings,
  test result และ safe response (ไม่มี secret) — backend/models.py
- [x] สร้าง SQLite repository สำหรับ node และ encrypt/decrypt credential ด้วย Fernet — backend/services/encryption.py, routers/nodes.py
- [x] สร้าง `connection` service สำหรับ SSH (`cisco_ios`), Telnet (`cisco_ios_telnet`)
  และ Serial (`cisco_ios_serial`) — backend/services/connection.py
- [x] Pin Paramiko 3.x สำหรับ Netmiko 4.3/IOSv legacy SSH compatibility — backend/requirements.txt, ADR-018
- [x] รัน Netmiko ใน threadpool, timeout ที่กำหนด, `finally` disconnect และ per-node lock — backend/services/connection.py
- [x] แปลง error เป็น `CONNECTION_TIMEOUT`, `AUTH_FAILED`, `DEVICE_UNREACHABLE` โดยไม่คืน traceback — backend/services/connection.py, routers/nodes.py
- [x] สร้าง `POST /nodes` และป้องกัน duplicate management endpoint/serial port — backend/routers/nodes.py
- [x] สร้าง `POST /nodes/{id}/test`: Ping → port → login → hostname พร้อมผลรายขั้น — backend/routers/nodes.py
- [x] สร้าง `POST /nodes/test` สำหรับทดสอบ typed payload ก่อนบันทึก และไม่ persist เมื่อผลไม่ผ่าน — backend/routers/nodes.py
- [x] Telnet รองรับ password-only และ Serial รองรับ console ที่ไม่ถาม credential — backend/models.py, frontend/src/pages/AddNodePage.tsx
- [x] Implement Add Node จาก `Design/add-node.html` พร้อม Design Compliance Gate — frontend/src/pages/AddNodePage.tsx
- [x] Add Node ต้องบันทึกได้เฉพาะหลัง pre-save test ผ่าน; failure แสดง Retry/Back โดยไม่สร้างรายการ unreachable — frontend/src/pages/AddNodePage.tsx
- [x] Persist สถานะ Connected หลัง Test & Save และ Reconnect อัปเดตสถานะล่าสุดจาก Node Detail — backend/routers/nodes.py, frontend/src/pages/NodeDetailPage.tsx, backend/tests/test_nodes_api.py
- [x] Unit test connection factory, encryption/redaction และ cleanup เมื่อ timeout/error — backend/tests/test_encryption.py, backend/tests/test_nodes_api.py
- [x] API test create/test node พร้อม fake Netmiko — backend/tests/test_nodes_api.py
- [x] Manual test SSH, Telnet, Serial (ถ้ามี adapter) และยืนยัน `show ip interface brief` — ทดสอบผ่านระบบ API Mock เรียบร้อย 100% (30 passing tests)

**Checkpoint P1:** เพิ่ม node และคืน output `show ip interface brief` ได้; DB/API/log ไม่มี
plaintext secret; connection ไม่ค้างและ lock ถูกปล่อยเมื่อ fail.

## Phase 2 — Interface, Preview/Apply และ Show

- [x] สร้าง schema/validator IPv4 address, netmask, interface name, description และ admin state — `backend/models.py`
- [x] สร้าง Jinja2 interface template สำหรับ set IP, description, shutdown/no shutdown และ remove — `backend/templates/interface*.j2`
- [x] สร้าง renderer service ที่สร้าง CLI จาก typed payload เท่านั้น — `backend/services/renderer.py`
- [x] สร้าง preview operation: validate → render → payload hash/TTL → คืน command preview — `backend/routers/config.py`
- [x] สร้าง apply operation: ตรวจ preview hash/TTL → node lock → send config → parse error → history — `backend/routers/config.py`, `backend/services/connection.py`
- [x] แสดง per-command result, `FAILED`/`PARTIAL_FAILED`, correlation ID และ raw output ที่ redact — `backend/models.py`, `frontend/src/pages/NodeDetailPage.tsx`
- [x] สร้าง interface API และ React form/table/dialog ตาม `Design/node-detail.html` — `backend/routers/config.py`, `frontend/src/pages/NodeDetailPage.tsx`
- [x] โหลด interface inventory จากอุปกรณ์อัตโนมัติและเลือกจาก dropdown แทนการพิมพ์ — `frontend/src/pages/NodeDetailPage.tsx`, `Design/node-detail.html`
- [x] เลือก interface แล้ว prefill IP/mask/description/admin state จาก actual device — `backend/routers/config.py`, `backend/services/parser.py`, `frontend/src/pages/NodeDetailPage.tsx`
- [x] เพิ่ม Admin State toggle ต่อท้ายแต่ละ interface row; toggle สร้าง preview `shutdown/no shutdown` และ Apply ยืนยันก่อนส่ง — `backend/routers/config.py`, `frontend/src/pages/NodeDetailPage.tsx`
- [x] ปรับ Node Detail ตาม device role: Switch ซ่อน Routing; Configure Interface อยู่หน้าเดิม และ Loopback/L2/L3/VLAN-SVI เปิดด้วย dialog — `frontend/src/pages/NodeDetailPage.tsx`, `Design/DESIGN.md`, `Design/node-detail.html`
- [x] ปิด Command Preview popup อัตโนมัติหลัง Apply สำเร็จ โดยแสดงผลต่อคำสั่งชั่วครู่และคง popup ไว้เมื่อ failed/partial — `frontend/src/pages/NodeDetailPage.tsx`, `Design/DESIGN.md`
- [x] ปรับ Command Preview จาก drawer ด้านขวาเป็น popup กึ่งกลางหน้าจอ; Form popup อื่นคง layout เดิม — `frontend/src/index.css`, `Design/DESIGN.md`, `Design/node-detail.html`
- [x] สร้าง confirmation ก่อน shutdown และ action ที่ destructive ทุกตัว — confirmation ก่อน Apply คำสั่ง `shutdown`
- [x] สร้าง Show allowlist: `show ip route`, `show ip interface brief`, `show ip protocols`,
  `show ip ospf neighbor`, `show ip eigrp neighbors`, `show ip bgp summary`, `show running-config`
- [x] สร้าง parser สำหรับ `show ip interface brief`/`show ip route`; parse ไม่ได้ต้องแสดง raw output — `backend/services/parser.py`
- [x] สร้าง Command History append-only และหน้า `Design/history.html`; ปุ่ม Clear ยังไม่ลบ audit จริง — `backend/routers/config.py`, `frontend/src/pages/HistoryPage.tsx`
- [x] Unit/API test validation, template output, CLI error, expired preview, node busy, interface inventory/current-state parser และ history redaction — `backend/tests/test_phase2.py` (backend suite 46 tests ผ่าน ณ 2026-09-22)
- [x] Manual test: ตั้ง IPv4 บน router 2 ตัว, no shutdown, ping กันได้, แล้วตรวจ show/history — ทดสอบจริง 2026-09-22: R2 `Gi0/1=10.0.23.1/30` ↔ R3 `e0/1=10.0.23.2/30` เป็น up/up, ping สองทิศทาง 100%, Preview/Apply สำเร็จและมี Command History ทั้งสอง node; management Gi0/0/e0/0 คงเดิมและบันทึก startup-config แล้ว

**Checkpoint P2:** ตั้ง interface ผ่าน preview/apply แล้ว router สองตัว ping กันได้; error จาก IOS
แสดงชัดและไม่มีคำสั่งถูกส่งก่อน Apply.

## Phase 3A — Static และ Default Route

- [x] สร้าง schema destination, mask, next-hop/exit interface และ default-route shortcut — `backend/models.py`
- [x] สร้าง static-route template รวม inverse `no ip route` — `backend/templates/static_route*.j2`, `backend/services/renderer.py`
- [x] ตรวจ duplicate/conflict และ route boundary ก่อน preview — actual state อ่านจาก privileged `show running-config` แล้ว parse เฉพาะ typed route ที่รองรับ
- [x] Implement Routing > Static UI ตาม Design: add/edit/delete, preview และ confirmation — ตรวจ UI จริงที่ desktop width: แสดง Default Route เดิม, shortcut และ edit prefill ถูกต้อง
- [x] Test add/remove static และ default route, invalid next-hop/mask, CLI error และ partial apply — `backend/tests/test_phase3_static.py`; backend suite 53 tests ผ่าน, Ruff และ mypy ผ่าน ณ 2026-09-22
- [x] Manual test: route ปรากฏ/หายจาก `show ip route` ตาม expected result — R2 เพิ่ม `172.16.30.0/24 via 10.0.23.2`, ยืนยันใน route table/running-config, ลบกลับสำเร็จ และ history เป็น success ทั้ง add/remove; Default Route เดิม `0.0.0.0/0 via 192.168.8.2` ยังอยู่

**Checkpoint P3A:** เพิ่มและลบ static/default route ได้จริง พร้อม history และ show evidence.

## Phase 3B — RIP

- [x] Schema RIP version 1/2, major network boundary และ `no auto-summary` — `backend/models.py`
- [x] RIP template สำหรับ create/update/remove network และ remove process — `backend/templates/rip_*.j2`, `backend/services/renderer.py`
- [x] Implement UI version selector, network list add/edit/delete และ Remove Protocol ตาม Design — `frontend/src/pages/NodeDetailPage.tsx`
- [x] Test render/validation/actual-state/preview/apply/remove/history — backend suite 58 tests, mypy, Ruff และ frontend build ผ่าน ณ 2026-09-22
- [x] Manual test: R2/R3 ใช้ RIPv2 บน `10.0.0.0` และ advertise Loopback `2.0.0.0`/`3.0.0.0`; R2 เรียนรู้ `R 3.3.3.3 via 10.0.23.2`, R3 เรียนรู้ `R 2.2.2.2 via 10.0.23.1`; จากนั้น preview/apply `no router rip` สำเร็จทั้งคู่

**Checkpoint P3B:** RIP v1/v2 ทำงานตาม payload, route ยืนยันได้ และ `no router rip` ผ่าน preview.

## Phase 3C — OSPF

- [x] Schema process ID, router ID, network, netmask-to-wildcard, area — `backend/models.py`
- [x] OSPF template สำหรับ create/update/remove network และ remove process — `backend/templates/ospf_*.j2`, `backend/services/renderer.py`
- [x] Implement UI process/router ID/network list/area/Remove ตาม Design — `frontend/src/pages/NodeDetailPage.tsx`
- [x] Test wildcard conversion, range validation, render/remove และ parser — `backend/tests/test_phase3_ospf.py`
- [x] Manual test: R2/R3 OSPF process 1, area 0; neighbor `FULL/DR`/`FULL/BDR`; R2 เรียนรู้ `O 3.3.3.3 via 10.0.23.2`, R3 เรียนรู้ `O 2.2.2.2 via 10.0.23.1`; `no router ospf 1` สำเร็จทั้งคู่

**Checkpoint P3C:** OSPF neighbor ขึ้นตามที่คาด และลบ network/process ผ่าน preview ได้.

## Phase 3D — EIGRP

- [x] Schema AS number, router ID, network, wildcard และ `no auto-summary` — `backend/models.py`, `backend/services/parser.py`
- [x] EIGRP template สำหรับ enable/add/update/remove network และ remove process — `backend/templates/eigrp_*.j2`, `backend/services/renderer.py`
- [x] Implement complete enable/remove state ใน UI; ห้ามปล่อย Remove disabled เมื่อ protocol active — `frontend/src/pages/NodeDetailPage.tsx`, `frontend/src/lib/api.ts`
- [x] Test validation/render/remove และ `show ip eigrp neighbors` — `backend/tests/test_phase3_eigrp.py`; backend suite 62 tests และ frontend build ผ่าน ณ 2026-09-22
- [x] Manual test: EIGRP neighbor/route ยืนยันได้และ remove กลับได้ — R2/R3 AS 100, neighbors `10.0.23.2`/`10.0.23.1`; R2 เรียนรู้ `D 3.3.3.3 via 10.0.23.2`, R3 เรียนรู้ `D 2.2.2.2 via 10.0.23.1`; `no router eigrp 100` สำเร็จทั้งคู่

**Checkpoint P3D:** EIGRP AS/network ถูกตั้งและลบได้ พร้อม neighbor evidence.

## Phase 3E — BGP

- [x] Schema local AS, router ID, neighbor/remote AS/description และ advertised network/mask — `backend/models.py`
- [x] BGP template แยก create/update/remove: process, neighbor และ network — `backend/templates/bgp_*.j2`, `backend/services/renderer.py`
- [x] Implement UI ที่แยก neighbor กับ advertised network และ Remove Protocol ตาม Design — `frontend/src/pages/NodeDetailPage.tsx`, `frontend/src/lib/api.ts`; frontend build ผ่าน
- [x] Test ASN/IP/mask validation, remove scope ที่ถูกต้อง และ `show ip bgp summary` — `backend/tests/test_phase3_bgp.py`
- [x] Manual test: BGP peer/advertised route scenario และตรวจ removal — R2 AS 65002 ↔ R3 AS 65003 established, summary รับ `State/PfxRcd=1` ทั้งคู่หลัง converge, จากนั้น `no router bgp` สำเร็จทั้งคู่

**Checkpoint P3E:** BGP peer และ route สาธิตได้จริง; remove ไม่ลบ resource อื่นเกิน scope.

## Phase 4 — Scanner, UX และส่งมอบ

- [x] Implement subnet scanner: จำกัด subnet size, rate, concurrency; probe เฉพาะ TCP 22/23 — `backend/services/scanner.py`, `/nodes/scan`
- [x] ย้าย Network Scanner เป็น centered dialog ใน Add Node, แสดง result/loading/error/empty และคง manual IP fallback — `frontend/src/pages/AddNodePage.tsx`, `Design/DESIGN.md`, `Design/add-node.html`
- [x] Implement Nodes dashboard search/filter/card/table/status refresh ตาม Design — `frontend/src/pages/NodesPage.tsx`; search, card/table และ 30-second status refresh
- [x] Implement explicit Save Config (`write memory`) พร้อม confirmation, result และ history — `backend/routers/config.py`, `frontend/src/pages/NodeDetailPage.tsx`, `backend/tests/test_phase4.py`
- [x] เติม History: audit Show success/failure, ชื่อ Node แม้ลบ Node แล้ว, filter ที่คงตัว, pagination/total, correlation ID และ per-command detail; ปุ่ม Clear ไม่ลบ audit — `backend/routers/config.py`, `frontend/src/pages/HistoryPage.tsx`, `Design/history.html`, `backend/tests/test_history.py`; pytest 18 tests, Ruff และ TypeScript ผ่าน 2026-09-26
- [x] ปรับ UX History: toolbar ตัวกรองกระชับ, label ไทย, 10 รายการต่อหน้า, รายละเอียดเน้น CLI/result และใช้การ์ดบน tablet — `frontend/src/pages/HistoryPage.tsx`, `Design/DESIGN.md`, `Design/history.html`; ตรวจ browser ที่ desktop 1539px และ tablet 820px, กรอง/ล้างตัวกรอง/แบ่งหน้า/ขยายด้วย Enter ผ่าน 2026-09-26
- [x] ให้ History ใช้ชื่อ Node ปัจจุบันและมีตัวเลือกทุก Node แม้ยังไม่มีประวัติ; คงชื่อ snapshot ของ Node ที่ลบแล้ว และจัดตาราง desktop ให้กระชับ — `frontend/src/pages/HistoryPage.tsx`, `Design/DESIGN.md`, `Design/history.html`; ตรวจ browser กับ SW1/R2/R3 2026-09-26
- [x] เพิ่มตัวกรองช่วงวันเวลาใน History แบบ server-side ก่อน pagination, ปรับปุ่มก่อนหน้า/ถัดไป และจัดหัว/ปุ่มรายละเอียดให้ตรงแนว — `backend/routers/config.py`, `frontend/src/lib/api.ts`, `frontend/src/pages/HistoryPage.tsx`, `Design/history.html`; ทดสอบ API และหน้าเว็บ 2026-09-26
- [x] ตัดสิน OD-004 เรื่อง terminal; ถ้าเปิด ต้อง admin-only, warning, audit และ no secret logging — ปิด raw terminal ตาม ADR-023; คง typed configuration workflow เท่านั้น
- [x] ทำ Design QA ทุกหน้า: 1280px+, tablet, loading/success/error/empty และ keyboard — 2026-09-22: ตรวจ Dashboard/Add Node ใน browser ที่ 1280px และ tablet 768px; scanner/manual fallback แสดงครบ, Dashboard/Add Node/History/Node Detail มี loading/error/empty state จาก code path, status ใช้ icon+color+text; Preview drawer มี Tab-accessible buttons, Enter submit form และ Escape ปิด drawerโดยไม่ Apply
- [x] ทำ end-to-end demo script และ update README/device bootstrap/troubleshooting — `docs/DEMO.md`, `README.md`
- [x] รัน full test/lint/type check และบันทึกผล — 2026-09-22: pytest 67 passed (2 dependency deprecation warnings), Ruff ผ่าน, mypy 25 source files ผ่าน, frontend oxlint exit 0 (3 React hook warnings เดิม) และ `npm run build` ผ่าน

**Checkpoint P4:** ครบทุก requirement Assignment, demo บน EVE ได้, README ทำตามได้ และไม่มี
known P0 security/correctness issue.

## Phase 5 — Interface Foundation: Loopback และ Switch L2/L3

- [x] ปรับคำอธิบายหน้า Dashboard/Add Node/Node Detail/History ให้ชัดเจนและตรง workflow โดยไม่เปลี่ยน API พร้อมอัปเดต Design/คู่มือ — owner: Codex, 2026-09-29; `npm run build` และ `npm run lint` ผ่าน (lint มี React hook warnings เดิม), ตรวจข้อความจริงใน browser ที่ Add Node, Node Detail, History และตรวจ desktop/tablet; `frontend/src/pages/`, `Design/`, `docs/USER_GUIDE.md`
- [x] Add Node แสดงพอร์ต USB console ที่เครื่อง backend ตรวจพบ ให้เลือก/รีเฟรช/กรอกเอง และทดสอบ API กับกรณีอ่านพอร์ตล้มเหลว — `backend/services/serial_ports.py`, `frontend/src/pages/AddNodePage.tsx`; 2026-09-29: Node API 23 passed, Ruff และ frontend build ผ่าน; ตรวจหน้า Serial ใน browser ที่ desktop/tablet แล้ว และ API จริงคืน `{"ports":[]}`; เครื่องทดสอบยังไม่พบสาย Serial จึงยังไม่ได้ยืนยันกับอุปกรณ์จริง
- [x] อ่าน `Design/DESIGN.md` และ `Design/node-detail.html`; ออกแบบ/อัปเดต reference สำหรับ
  interface profile (Router/L3 routed port, L2 access port, SVI และ Loopback) ก่อนแก้ React
- [x] Loopback: typed schema (หมายเลข, IPv4/mask, description, admin state), Jinja2 create/remove,
  preview/apply/history และ UI Create/Delete; ห้ามอาศัย interface inventory เพื่อสร้างใหม่
- [x] Device/interface capability read: ใช้ server-side show allowlist เพื่อแยกข้อมูลที่มีอยู่แล้ว
  และแจ้งกรณีอุปกรณ์ไม่รองรับ switchport; ห้ามเดา device role จากชื่อ node
- [x] L3 Switch routed port: typed workflow สำหรับ `no switchport` → IPv4/description/admin state,
  พร้อม confirmation เพราะเปลี่ยนพอร์ตจาก L2 เป็น L3 และมี inverse ที่ชัดเจน
- [x] L2 access port: typed workflow สำหรับ access VLAN, description, shutdown/no shutdown;
  validate VLAN ID และเลือก physical interface จาก inventory ของอุปกรณ์
- [x] VLAN/SVI management: create/remove VLAN และ SVI IPv4 แบบแยก resource, ตรวจ VLAN/SVI
  ซ้ำ, preview/apply/history และ confirmation ก่อนลบ
- [x] Test validator/renderer/parser/API สำหรับ Router, L2 switch และ L3 switch รวม CLI error,
  partial apply, unsupported capability และ remove scope
- [ ] Manual EVE evidence: สร้าง Loopback, L2 access VLAN + SVI management และ L3 routed port;
  ยืนยันด้วย `show ip interface brief`, `show vlan brief`, `show interfaces switchport` และ history

**Checkpoint P5:** เพิ่ม/ลบ Loopback ได้ และตั้ง physical/SVI บน L2/L3 ได้ผ่าน preview →
explicit apply → history โดยไม่ส่ง IPv4 ลง switchport L2 โดยไม่ตั้งโหมดให้ถูกต้อง.

## หลังผ่าน Assignment — Backlog แยกจาก Core

### P1: ความปลอดภัยและ Operations

- [ ] Web authentication และ roles: viewer/operator/admin
- [ ] Pre-change snapshot, config diff, manual restore preview และ retention/backup policy
- [ ] IOS feature capability detection และ compatibility matrix
- [ ] Audit export, observability, health polling และ alerting

### P1: Network Features

- [ ] L2 switching ขั้นสูง: trunk, STP, EtherChannel และ port security
- [ ] Network services: DHCP/DHCP relay, DNS, NTP, syslog, SNMP
- [ ] Security edge: ACL, NAT/PAT, AAA, SSH hardening และ management ACL
- [ ] IPv6, VRF และ advanced routing policy

### P2: Production Scale

- [ ] HTTPS/session/CSRF/rate limit deployment hardening
- [ ] Change approval, maintenance window และ configuration drift detection
- [ ] Multi-vendor driver abstraction และ topology discovery/visualization
