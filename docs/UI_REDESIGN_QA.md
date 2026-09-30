# ผลตรวจ UI — Device Index (2026-09-30)

## ขอบเขต

เจ้าของ: Codex. เปลี่ยนเฉพาะหน้า Nodes และ shared navigation ตาม ADR-042.
อ่าน `Design/DESIGN.md`, `Design/index.html`, React page และ shared components ก่อนแก้.
Input/output API, schema, validation, การเชื่อมต่อ และ Preview/Apply ไม่เปลี่ยน.
เพิ่มเฉพาะ UX state: Table เป็นค่าเริ่มต้น, กรองสถานะ, Escape ล้างคำค้นและปิดเมนู tablet.

## ผลจริง

- `npm run build`: ผ่าน รวม TypeScript และ Vite; warning เดิมเรื่อง config loader/chunk size.
- `npm run lint`: ผ่าน; 4 warnings เดิมอยู่ใน `NodeDetailPage.tsx`.
- Browser: Table/Cards, ค้นหาไม่พบ, Escape ล้างคำค้น, กรอง Connected ไม่พบ และล้างตัวกรองผ่าน.
- Enter เปิด Configure R3 และ Add Node ไป URL เดิมได้. Tab จากช่องค้นหาไปตัวกรองสถานะได้.
- เมนู tablet เปิดและปิดด้วย Escape ได้.
- Desktop 1441px, tablet 820px, mobile 390px และหน้าจอผู้ใช้ 1730px: document ไม่ล้นแนวนอน.
- ตารางที่จอเล็กเลื่อนแนวนอนได้ภายในกรอบ; Cards เป็นทางเลือกที่เห็น action ครบโดยไม่เลื่อนแนวนอน.
- Status ใช้ color + Lucide icon + text. สีสถานะไม่เปลี่ยนความหมาย.
- Detector รันหนึ่งครั้ง พบ animation ของ margin/width; ตัดสอง transition นี้แล้ว ไม่รัน detector ซ้ำ.
- Loading, backend error, retry, ไม่มี Node และ delete pending/error ตรวจจาก code path;
  ไม่ได้หยุด backend หรือเปลี่ยนข้อมูลจริงเพื่อจำลอง state เหล่านี้.

## หลักฐาน

ภาพจริงอยู่ใน `.impeccable/review/`: `desktop.png`, `tablet.png`, `mobile-table.png`,
`mobile.png` (Cards ทั้งหน้า) และ `user.png` (1730px). Browser export เพิ่มขอบว่างจาก zoom;
เก็บ raw ไว้และ crop เฉพาะขนาด document ที่อ่านจาก DOM โดยไม่แก้เนื้อหาในภาพ.

Plan review: receipt approved และ `plates → hero` ผ่าน (ไม่มี raster assets ที่ต้องผลิต).
Automated comp gate ยังอยู่ที่ hero: comparison มี drift/missing region และไม่ผ่าน hard gate.
Final diff อยู่ที่ `.impeccable/review/diff/final/`; score 78% ไม่เท่ากับ checkpoint ผ่าน.
Copy ไทย, filter สถานะ, icon library และการไม่แสดง “example data” เป็น adaptation ของ production;
ไม่มีข้อมูล Node ปลอมหรือการเลือก row ปลอม.

## เหตุการณ์ระหว่างทดสอบ

ทดสอบปุ่มลบ Rtest เปิด native confirmation แล้ว browser automation ค้าง.
หลังคืน browser พบ Rtest ถูกลบจริง; audit `Node Delete` เวลา `2026-09-30T09:08:13.092604+00:00`.
ไม่ได้ตั้งใจยืนยันลบ; ไม่สามารถยืนยันสาเหตุการตอบรับ native dialog จาก API ของ browser ได้.
History เดิมยังอยู่และ config อุปกรณ์ไม่ได้เปลี่ยน. หยุดทดสอบปุ่มลบทันทีและแจ้งผู้ใช้แล้ว.
ตรวจ `netconfig.db` ไม่พบ Rtest สำหรับกู้คืน. รอผู้ใช้ยืนยันค่าการเชื่อมต่อเดิมก่อนเพิ่มกลับ;
ไม่เดา baud rate/credential และไม่เขียนฐานข้อมูลเพื่อข้าม Test Connection.

## Checkpoint

Fresh finish-reviewer ตรวจภาพครบและให้ **fix** เฉพาะ process/incident; ไม่พบ UI correction
ที่จำเป็นใน scope นี้. ผลอยู่ที่ `.impeccable/review/finish-review.md`.
Verdict pass ให้ **ship เฉพาะสองรายการ handling ที่ตรวจซ้ำ**: เก็บ gate pending ตามจริง
และบันทึกเหตุการณ์/เงื่อนไขกู้ Rtest แล้ว; ไม่ใช่การรับรองว่า engine ผ่านหรือกู้ Rtest สำเร็จ.
UI implementation/build และการตรวจหลักผ่าน แต่ยังไม่ประกาศ checkpoint ทั้งงานผ่าน:
strict comp gate และข้อสรุปการกู้ Rtest ยัง pending; บันทึก token และส่วนประกอบจากโค้ดจริง
ใน `DESIGN.md` และ `.impeccable/design.json` แล้ว โดยรักษา baseline ของหน้าฟอร์มเดิม.
คำสั่ง finish disposition ship ถูก engine ปฏิเสธ เพราะ hero/sections/motion/responsive
ยังไม่ปิด; คงผล pending ตามจริง ไม่ข้ามหรือปลอมผล checkpoint.
ไม่มีการ push Git ในงานนี้.
