# NetConfig — การวิเคราะห์ความครบถ้วนของระบบ Config

ให้ใช้ร่วมกับ `../AGENTS.md` เพื่อกำหนด scope ของงาน.

## ข้อสรุป

Design ครอบคลุม **Assignment 2 core IPv4 routing UI** ได้ดี: dashboard, add node wizard,
interface, static/default route, RIP/OSPF/EIGRP/BGP, show, command preview, CLI และ history
ปรากฏใน `Design/`. แต่ยังเป็น prototype HTML และยังไม่ใช่ระบบ config ที่ “ครบทุกมิติ” สำหรับ
งานจริง. ขอบเขตที่ควรยืนยันคือ **ครบตาม Assignment เมื่อ implement และผ่าน acceptance tests**;
ส่วน enterprise operations/security ต้องทำเป็น backlog ไม่ควรแอบรวมจนทำให้ Phase 1–4 หลุด.

## Coverage เทียบโจทย์และ Design

| มิติ | สถานะของ Design | สิ่งที่ implementation ต้องทำจึงนับว่าครบ |
|---|---|---|
| Node dashboard/history | มี card/table, filter, expandable history | API, pagination/retention, immutable audit และ redaction |
| Add node | มี manual IP, SSH/Telnet/Serial, test steps | scanner subnet ตามโจทย์, credential encryption, real Ping/port/login/hostname, duplicate node handling |
| Connection | UI ระบุ 3 transport | Netmiko device type/serial params, timeout, cleanup, node lock, test failure mapping |
| Interface IPv4 | มี table, IP/mask/description, shutdown toggle | validate address/mask, load actual interface, preview/apply/remove และ confirmation |
| Static/default | มี add/edit/delete และ exit interface | validate destination/mask/next-hop, default route shortcut, inverse `no ip route`, duplicate/conflict checks |
| RIP | มี network และ remove | version 1/2 selector, `no auto-summary`, precise remove network/process, `show ip protocols` |
| OSPF | มี process/router-id/network/wildcard/area | typed process setup, wildcard generated from mask, remove entry/process และ neighbor verification |
| EIGRP | มี AS/router-id/network/wildcard | `no auto-summary`, complete enable/remove flow และ neighbor verification |
| BGP | มี local AS/router-id/neighbor/network | separate neighbor/network contracts, remove neighbor/network/process และ summary verification |
| Show | มี UI มากกว่าข้อกำหนด | required 7 commands ต้องมี allowlist, parser/raw fallback และ history |
| Preview/apply | มี drawer และ per-line mock result | operation TTL/hash, backend rendering, CLI error detection, partial failure state/audit |
| Save config | มี modal | explicit `write memory`, result capture, warning before persistence |

## ช่องว่างสำคัญก่อนเรียกว่าใช้งานปลอดภัย

### P0 — ต้องมีใน Phase 1–4 / ก่อน demo ที่ส่งผลกับ device

1. **Authentication/authorization ของ Web UI ยังไม่มีใน Design** — ทุกคนที่เปิด UI ไม่ควร
   อ่าน/ใช้ credential หรือ apply config ได้. อย่างน้อยแยก viewer/operator/admin เมื่อไม่ได้
   รันบนเครื่องส่วนตัวที่ไว้ใจได้ทั้งหมด.
2. **Secret lifecycle** — encryption at rest อย่างเดียวไม่พอ: ต้องมี Fernet key จาก environment,
   redaction, ไม่ log password, backup policy และ failure เมื่อ key หาย/เปลี่ยน.
3. **Concurrency + idempotency** — ต้อง lock per node และผูก Apply กับ preview hash; มิฉะนั้น
   สองแท็บอาจเขียน config ทับกันหรือ apply command คนละชุด.
4. **Partial failure/recovery** — IOS ไม่ transaction. ต้องเก็บ pre-change snapshot, result ต่อ
   คำสั่ง และแจ้ง state ที่อาจค้าง; ไม่โฆษณา rollback อัตโนมัติถ้ายังไม่มี.
5. **CLI terminal ขัดกับ safe workflow ได้** — แบบมี CLI raw command แต่โจทย์บังคับ config
   ผ่าน validation/template. ให้เป็น optional admin-only, warning/audit หรือซ่อนไว้ในรุ่นแรก.
6. **Scanner ในโจทย์ยังไม่ปรากฏเป็น flow จริงใน HTML** — Design บอก scan แต่หน้าจอรับ IP
   โดยตรง. ต้องเพิ่ม subnet scan results, limit subnet/rate/concurrency และ manual fallback.
7. **Device capability/IOS compatibility** — รองรับ IOS รุ่นต่างกันไม่เท่ากัน. Test connection
   ควรอ่าน platform/version แล้ว feature ต้องบอก unsupported ก่อน preview/apply.

### P1 — ทำต่อหลังผ่าน Assignment core

| มิติ | สิ่งที่ยังไม่ครอบคลุม | ผลกระทบ |
|---|---|---|
| L2 switching | VLAN, trunk/access, SVI, STP, EtherChannel, port-security | Design พูดถึง switch แต่ config core เป็น L3 router เป็นหลัก |
| Network services | DHCP/DHCP relay, DNS, NTP, syslog, SNMP/telemetry | ดูแลบริการและเวลา/monitoring ไม่ได้ |
| Security edge | ACL, NAT/PAT, AAA/RBAC, SSH hardening, management ACL, banners | ไม่พร้อมใช้ใน production หรือ multi-user lab |
| IPv6/segmentation | IPv6 interfaces/routes/OSPFv3/BGP, VRF | scope ปัจจุบัน IPv4 เท่านั้น |
| Routing depth | OSPF passive/default/area type, EIGRP metric/passive, BGP policy/filter/prefix-list | BGP/Routing UI เหมาะ lab basic ไม่ใช่ policy control |
| Operations | config diff/version/backup/restore/export, scheduled config, health polling/alerts | กู้คืนและติดตาม drift ยาก |
| Topology | CDP/LLDP discovery, topology visualization, interface mapping | UI แสดง node แยกกัน ไม่เห็นความสัมพันธ์ |

### P2 — ใช้เมื่อขยายเป็น production

- HTTPS/TLS deployment, CSRF/CORS policy, session expiry, rate limits และ audit export/retention
- HA/database backup, secret rotation, event logs/metrics/tracing และ disaster recovery drills
- Approval workflow/change window, maintenance mode, configuration compliance/drift detection
- Multi-vendor driver abstraction; ห้ามอ้างว่า support ทั้งหมดจาก `cisco_ios` driver เดียว

## ลำดับส่งมอบที่แนะนำ

1. ทำ Phase 1 connection foundation พร้อม encryption/redaction/error contract/node lock.
2. ทำ Interface + Show พร้อม preview/apply/history เป็น reference vertical slice.
3. ทำ routing ทีละ protocol โดย reuse contract/template/test matrix เดียวกัน.
4. ทำ scanner และ UX polish ตาม Design; ปิด raw CLI default.
5. เมื่อ Assignment ผ่านแล้ว จัด P1 เป็น epics แยก ไม่ยัดรวมใน core.

## Acceptance matrix ที่ต้องใช้ตอนตรวจ

| Use case | Expected evidence |
|---|---|
| เพิ่ม SSH/Telnet/Serial node | test output และ DB ไม่มี plaintext secret |
| Invalid form | frontend block + backend `VALIDATION_ERROR`; ไม่มี connection/device command |
| Preview | commands ตรง template, ยังไม่มี history apply/device mutation |
| Apply valid config | per-command success, `show` ยืนยัน, immutable history record |
| CLI error/timeout | message ไทย + correlation ID, raw output redact, disconnect/lock released |
| Delete/shutdown/save | confirmation → preview → apply, inverse/result history ครบ |
| OSPF/EIGRP/BGP | neighbor/route show ยืนยันตาม protocol และ remove แล้วตรวจ state ใหม่ |

## Design observations ที่ควรแก้เมื่อ implement

- `Design/node-detail.html` มี show commands เพิ่มเติม (CDP, version, topology) ซึ่งดีได้ แต่
  backend ต้อง declare allowlist ไม่เปิด arbitrary show.
- Mock UI แสดง EIGRP/BGP Remove disabled แม้มี delete dialog; implementation ต้องทำ behavior
  ให้สอดคล้องและครบข้อกำหนด “ทุก protocol ลบ config ได้”.
- Command History มี Clear History; ให้เปลี่ยนเป็น filter/hide หรือ privileged retention action
  จนกว่าจะตัดสิน policy audit.
- หน้าจอ Add Node ระบุ device type Router/Switch แต่ core config ยังไม่มี L2 feature; แสดง
  capability/status ชัดเจนเพื่อไม่ให้ผู้ใช้คิดว่า switch configuration ครบแล้ว.
